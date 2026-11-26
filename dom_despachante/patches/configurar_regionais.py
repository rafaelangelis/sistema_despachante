"""Aplica fuso e formatos do Brasil em sites instalados antes de install.configurar_regionais existir."""

from dom_despachante.install import configurar_regionais


def execute():
	configurar_regionais()
