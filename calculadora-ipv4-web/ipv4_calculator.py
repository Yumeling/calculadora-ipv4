"""Lógica de cálculo y clasificación de direcciones IPv4.

Los cálculos de red se realizan con la biblioteca estándar ipaddress.
"""

from __future__ import annotations

import re
from ipaddress import IPv4Address, IPv4Network
from typing import Any


class IPv4InputError(ValueError):
    """Error controlado de validación de los datos IPv4 ingresados."""


_OCTET_RE = re.compile(r"^(0|[1-9][0-9]{0,2})$")
_PREFIX_RE = re.compile(r"^(0|[1-9][0-9]?)$")


def parse_ipv4(value: Any, field_name: str = "dirección IPv4") -> IPv4Address:
    """Valida cuatro octetos decimales entre 0 y 255."""
    if not isinstance(value, str):
        raise IPv4InputError(f"La {field_name} debe ser un texto IPv4 válido.")

    value = value.strip()
    octets = value.split(".")
    if len(octets) != 4:
        raise IPv4InputError(
            f"La {field_name} debe contener exactamente cuatro octetos separados por puntos."
        )

    for index, octet in enumerate(octets, start=1):
        if not _OCTET_RE.fullmatch(octet):
            raise IPv4InputError(
                f"El octeto {index} de la {field_name} no es válido. Use enteros decimales de 0 a 255."
            )
        if int(octet) > 255:
            raise IPv4InputError(
                f"El octeto {index} de la {field_name} está fuera de rango (0 a 255)."
            )

    return IPv4Address(value)


def parse_prefix(value: Any) -> int:
    """Valida un prefijo CIDR comprendido entre 0 y 32."""
    if isinstance(value, bool):
        raise IPv4InputError("El prefijo CIDR debe ser un entero entre 0 y 32.")

    text = str(value).strip()
    if not _PREFIX_RE.fullmatch(text):
        raise IPv4InputError("El prefijo CIDR debe ser un entero entre 0 y 32.")

    prefix = int(text)
    if not 0 <= prefix <= 32:
        raise IPv4InputError("Prefijo fuera de rango: use un valor entre 0 y 32.")
    return prefix


def mask_to_prefix(mask_text: Any) -> int:
    """Convierte una máscara decimal contigua a prefijo CIDR."""
    mask = parse_ipv4(mask_text, "máscara decimal")
    mask_number = int(mask)
    inverted = (~mask_number) & 0xFFFFFFFF

    # Una máscara es contigua si los bits invertidos tienen la forma 00...0011...11.
    if inverted & (inverted + 1):
        raise IPv4InputError(
            "La máscara decimal no es contigua. Los bits 1 deben estar seguidos por los bits 0."
        )

    return mask_number.bit_count()


def traditional_class(address: IPv4Address) -> str:
    """Devuelve la clase IPv4 histórica según el primer octeto."""
    first = int(str(address).split(".")[0])
    if first <= 127:
        if first == 0:
            return "A (bloque 0/8 reservado)"
        if first == 127:
            return "A (bloque 127/8 reservado para loopback)"
        return "A"
    if first <= 191:
        return "B"
    if first <= 223:
        return "C"
    if first <= 239:
        return "D (multicast)"
    return "E (reservada / uso especial)"


# Parte de RFC 1918. 
_PRIVATE_NETWORKS = tuple(
    IPv4Network(block)
    for block in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    )
)

# Asignaciones especiales de IANA que tienen alcance global
_IANA_GLOBAL_SPECIAL = tuple(
    (IPv4Network(block), name)
    for block, name in (
        ("192.0.0.9/32", "Port Control Protocol Anycast"),
        ("192.0.0.10/32", "Traversal Using Relays around NAT Anycast"),
        ("192.31.196.0/24", "AS112-v4"),
        ("192.52.193.0/24", "AMT"),
        ("192.175.48.0/24", "Direct Delegation AS112 Service"),
    )
)

# Parte de uso especial o no global incluidos en el registro de IANA
_SPECIAL_NETWORKS = tuple(
    (IPv4Network(block), name)
    for block, name in (
        ("0.0.0.0/32", "Dirección no especificada"),
        ("255.255.255.255/32", "Broadcast limitado"),
        ("0.0.0.0/8", "Este equipo / red actual (0/8)"),
        ("100.64.0.0/10", "Espacio de direcciones compartido (CGNAT)"),
        ("127.0.0.0/8", "Loopback"),
        ("169.254.0.0/16", "Link-local"),
        ("192.0.0.0/24", "Asignaciones de protocolos IETF"),
        ("192.0.2.0/24", "Documentación TEST-NET-1"),
        ("192.88.99.0/24", "Relay 6to4 obsoleto"),
        ("198.18.0.0/15", "Pruebas de rendimiento / benchmarking"),
        ("198.51.100.0/24", "Documentación TEST-NET-2"),
        ("203.0.113.0/24", "Documentación TEST-NET-3"),
        ("224.0.0.0/4", "Multicast"),
        ("240.0.0.0/4", "Reservada (clase E)"),
    )
)


def classify_address(address: IPv4Address) -> dict[str, Any]:
    """Clasifica la dirección ingresada, no todo el bloque de subred."""
    for network in _PRIVATE_NETWORKS:
        if address in network:
            return {
                "category": "Privada (RFC 1918)",
                "detail": f"Pertenece al bloque privado {network}.",
                "special_range": str(network),
                "global_reachable": False,
            }

    for network, name in _IANA_GLOBAL_SPECIAL:
        if address in network:
            return {
                "category": "Pública global",
                "detail": f"Asignación especial de IANA: {name}; el registro la marca como globalmente alcanzable.",
                "special_range": str(network),
                "global_reachable": True,
            }

    for network, name in _SPECIAL_NETWORKS:
        if address in network:
            return {
                "category": "Propósito especial / no global",
                "detail": f"{name} ({network}). No se trata como una dirección pública global convencional.",
                "special_range": str(network),
                "global_reachable": False,
            }

    return {
        "category": "Pública global",
        "detail": "No pertenece a los bloques privados RFC 1918 ni a los bloques especiales/no globales contemplados.",
        "special_range": None,
        "global_reachable": True,
    }


def calculate_ipv4(
    *,
    cidr: str | None = None,
    ip: str | None = None,
    prefix: Any = None,
    mask: str | None = None,
) -> dict[str, Any]:
    """Calcula información de una dirección IPv4 con CIDR o máscara decimal.

    Entradas admitidas:
      - cidr="192.168.10.25/27"
      - ip="192.168.10.25", prefix="27"
      - ip="192.168.10.25", mask="255.255.255.224"
    """
    if cidr is not None:
        if ip is not None or prefix is not None or mask is not None:
            raise IPv4InputError("Use la entrada CIDR o la entrada IP + máscara/prefijo, no ambas.")
        if not isinstance(cidr, str) or cidr.count("/") != 1:
            raise IPv4InputError("Formato CIDR incorrecto. Ejemplo: 192.168.10.25/27.")
        address_text, prefix_text = (part.strip() for part in cidr.split("/", 1))
        address = parse_ipv4(address_text)
        prefix_length = parse_prefix(prefix_text)
        input_format = "CIDR"
    else:
        if ip is None:
            raise IPv4InputError("Ingrese una dirección IPv4.")
        if prefix is not None and mask is not None:
            raise IPv4InputError("Ingrese el prefijo CIDR o la máscara decimal, no ambos.")
        address = parse_ipv4(ip)
        if mask is not None:
            prefix_length = mask_to_prefix(mask)
            input_format = "IP + máscara decimal"
        elif prefix is not None:
            prefix_length = parse_prefix(prefix)
            input_format = "IP + prefijo CIDR"
        else:
            raise IPv4InputError("Falta la máscara decimal o el prefijo CIDR.")

    network = IPv4Network((address, prefix_length), strict=False)
    total_addresses = network.num_addresses
    subnet_mask = str(network.netmask)
    wildcard_mask = str(network.hostmask)

    notes: list[str] = []
    directed_broadcast: str | None
    usable_hosts: int | None
    first_usable: str | None
    last_usable: str | None

    first_octet = int(str(address).split(".")[0])
    non_unicast_class = first_octet >= 224
    if non_unicast_class:
        directed_broadcast = None
        usable_hosts = None
        first_usable = None
        last_usable = None
        if first_octet <= 239:
            notes.append(
                "Clase D (multicast): esta dirección no es un host unicast convencional. "
                "Se omiten la cantidad y el rango de hosts utilizables, así como el broadcast dirigido."
            )
        else:
            notes.append(
                "Clase E (reservada/uso especial): no se interpreta como una subred de hosts "
                "unicast convencional. Se omiten la cantidad y el rango de hosts utilizables, "
                "así como el broadcast dirigido."
            )
    elif prefix_length == 32:
        directed_broadcast = None
        usable_hosts = None
        first_usable = None
        last_usable = None
        notes.append(
            "Prefijo /32: representa una única dirección IPv4 o una ruta de host. "
            "No se calcula un rango convencional de hosts ni un broadcast dirigido."
        )
    elif prefix_length == 31:
        directed_broadcast = None
        usable_hosts = 2
        first_usable = str(network.network_address)
        last_usable = str(network.broadcast_address)
        notes.append(
            "Prefijo /31: siguiendo RFC 3021 para enlaces punto a punto, las dos "
            "direcciones del bloque son utilizables y no existe broadcast dirigido para ese enlace."
        )
    else:
        directed_broadcast = str(network.broadcast_address)
        usable_hosts = max(total_addresses - 2, 0)
        first_usable = str(network.network_address + 1) if usable_hosts else None
        last_usable = str(network.broadcast_address - 1) if usable_hosts else None
        if prefix_length == 0:
            notes.append(
                "Prefijo /0: se muestran los resultados aritméticos del bloque completo IPv4. "
                "No debe interpretarse como una subred LAN convencional; incluye rangos especiales."
            )
        elif prefix_length == 30:
            notes.append("Prefijo /30: bloque convencional con dos direcciones de host utilizables.")

    if prefix_length not in (31, 32) and address == IPv4Address("255.255.255.255"):
        notes.append(
            "La dirección ingresada es el broadcast limitado IPv4 (255.255.255.255), "
            "no una dirección unicast de host convencional."
        )

    return {
        "input_format": input_format,
        "address": str(address),
        "prefix_length": prefix_length,
        "subnet_mask": subnet_mask,
        "wildcard_mask": wildcard_mask,
        "network_address": str(network.network_address),
        "directed_broadcast": directed_broadcast,
        "total_addresses": total_addresses,
        "usable_hosts": usable_hosts,
        "first_usable_host": first_usable,
        "last_usable_host": last_usable,
        "traditional_class": traditional_class(address),
        "classification": classify_address(address),
        "notes": notes,
    }
