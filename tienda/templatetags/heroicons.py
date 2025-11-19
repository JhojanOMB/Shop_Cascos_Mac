# tienda/templatetags/heroicons.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Mapa clave -> SVG (Heroicons mini, inline). Ajusta tamaños/clases si quieres.
SVG_MAP = {
    'tag': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 7h.01M5 7a2 2 0 012-2h2l8 8-4 4L5 9V7z"/></svg>',
    'pencil': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536M4 20h4.586a1 1 0 00.707-.293l9.414-9.414a2 2 0 000-2.828l-3.536-3.536a2 2 0 00-2.828 0L3.707 13.293A1 1 0 003 14v4a1 1 0 001 1z"/></svg>',
    'hash': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 16h10M9 4v16M15 4v16"/></svg>',
    'currency': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2"/></svg>',
    'list': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>',
    'photo': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 14l2.5-3 2 2.5L16 10l4 6H4z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'book': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 20H6a2 2 0 01-2-2V6a2 2 0 012-2h6" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/><path d="M18 20h-6V4h6a2 2 0 012 2v12a2 2 0 01-2 2z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'users': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M17 20h5v-2a4 4 0 00-3-3.87M9 20H4v-2a4 4 0 013-3.87" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/><path d="M16 11a4 4 0 11-8 0 4 4 0 018 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'badge': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2l3 7 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1 3-7z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'tag': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M7 7h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'ruler': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 21l18-18M8 6h.01M12 10h.01M16 14h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'box': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M21 16V8a2 2 0 00-1-1.73L12 3 4 6.27A2 2 0 003 8v8a2 2 0 001 1.73L12 21l8-3.27A2 2 0 0021 16z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'swatch': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M20 12a8 8 0 11-16 0 8 8 0 0116 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'user': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M16 14a4 4 0 10-8 0"/><path d="M12 14v6"/></svg>',
    'phone': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 16.92V21a2 2 0 01-2.18 2A19.86 19.86 0 013 5.18 2 2 0 015 3h4.09a1 1 0 01.99.86 12.44 12.44 0 01-.56 3.11 1 1 0 00.24.9l2.2 2.2a1 1 0 00.9.24 12.44 12.44 0 013.11-.56 1 1 0 01.86.99V16.92z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'mail': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8"/><path d="M21 8v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
    'question': '<svg xmlns="http://www.w3.org/2000/svg" class="{class_}" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M8 10a4 4 0 118 0c0 2-2 3-2 3"/><path d="M12 18h.01" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"/></svg>',
}

@register.simple_tag
def hero_icon(key, class_='w-5 h-5 text-gray-500'):
    svg = SVG_MAP.get(key)
    if not svg:
        svg = SVG_MAP['question']
    return mark_safe(svg.format(class_=class_))
