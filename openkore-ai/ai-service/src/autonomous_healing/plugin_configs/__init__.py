"""
Plugin configuration generators for autonomous self-healing

This package contains modules that automatically generate plugin configurations
when plugins report missing or invalid config keys, eliminating the need for
manual config.txt edits.
"""

from .teledest_generator import TeleDestConfigGenerator, generate_teledest_config

__all__ = ['TeleDestConfigGenerator', 'generate_teledest_config']
