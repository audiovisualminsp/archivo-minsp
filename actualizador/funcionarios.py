# -*- coding: utf-8 -*-
"""Funcionarios del Ministerio y cómo los nombra la gente.

Para sumar uno nuevo: agregarlo en FUNCIONARIOS con su área, y si se lo
suele nombrar de otra forma (nombre de pila, cargo), sumar esa forma en ALIAS.
"""

FUNCIONARIOS = {
 'López':       'Ministro de Infraestructura y Servicios Públicos',
 'Castelló':    'Infraestructura Hídrica y Gasífera',
 'Tuninetti':   'Infraestructura Eléctrica y Arquitectura',
 'Mansur':      'Planificación Energética',
 'Toneatto':    'Sub secretaría de Infraestructura Hídrica',
 'Caparroz':    'Sub secretaría de Arquitectura',
 'Turletto':    'Sub secretaría de Infraestructura Eléctrica',
 'Gabutti':     'Transición Energética',
 'Santillan':   'BioEnergía',
 'Chicala':     'Sub secretaría de Saneamiento',
 'Brandan':     'Coordinación Territorial',
 'Borello':     'Sub secretaría de Infraestructura Gasífera',
 'Testagrossa': 'Coordinación Legal y Administrativa',
 'Prone':       'Dirección de Espacios Verdes',
}

ALIAS = {
 'el ministro':     'López',
 'la ministra':     'López',
 'ministro':        'López',
 'fabian lopez':    'López',
 'fabian':          'López',
 'lopez':           'López',
 'edgar castello':  'Castelló',
 'edgar':           'Castelló',
 'mariano santillan':'Santillan',
 'mariano':         'Santillan',
}
