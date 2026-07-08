"""
SINAPSID Medical Library Module
================================
Maneja la lectura y parsing de archivos Markdown de investigación médica
desde memory/medical-library/
"""

import os
import re
from datetime import datetime
from pathlib import Path

# Rutas a los directorios de la biblioteca
LIBRARY_BASE = Path('/home/xiu/.openclaw/workspace/memory/medical-library')
SEARCHES_DIR = LIBRARY_BASE / 'searches'
STUDY_OF_DAY_DIR = LIBRARY_BASE / 'study-of-day'
MONITOR_DIR = LIBRARY_BASE / 'monitor'


def parse_markdown_file(filepath):
    """Parsea un archivo Markdown y extrae metadatos y contenido."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraer frontmatter si existe
        frontmatter = {}
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            content = content[frontmatter_match.end():]
            
            # Parsear frontmatter simple
            for line in frontmatter_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip().strip('"').strip("'")
        
        # Extraer título (primer H1)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else os.path.basename(filepath).replace('.md', '').replace('_', ' ').title()
        
        # Extraer resumen (primeros ~300 caracteres de contenido relevante)
        # Limpiar markdown básico
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # Quitar imágenes
        clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)  # Quitar links
        clean_text = re.sub(r'[#*_`]', '', clean_text)  # Quitar markdown
        clean_text = re.sub(r'\n+', ' ', clean_text)  # Quitar saltos de línea
        clean_text = clean_text.strip()
        
        # Resumen: primeros ~300 caracteres
        summary = clean_text[:300] + '...' if len(clean_text) > 300 else clean_text
        
        # Extraer PMIDs si existen
        pmids = re.findall(r'PMID:\s*(\d+)', content)
        
        # Extraer tags/categorías del contenido
        tags = []
        if 'vasopresina' in content.lower() or 'norepinephrine' in content.lower() or 'choque séptico' in content.lower():
            tags.append('Hemodinamia')
        if 'peep' in content.lower() or 'ards' in content.lower() or 'ventilator' in content.lower():
            tags.append('Ventilatorio')
        if 'delirium' in content.lower() or 'sedaci' in content.lower():
            tags.append('Neurología')
        if 'renal' in content.lower() or 'dialisis' in content.lower():
            tags.append('Renal')
        if 'meta-análisis' in content.lower() or 'meta-analysis' in content.lower():
            tags.append('Meta-análisis')
        if 'rct' in content.lower() or 'randomized' in content.lower():
            tags.append('RCT')
        
        # Fecha del archivo
        stat = os.stat(filepath)
        date_created = datetime.fromtimestamp(stat.st_mtime)
        
        return {
            'id': os.path.basename(filepath).replace('.md', ''),
            'filename': os.path.basename(filepath),
            'title': title,
            'summary': summary,
            'content': content,
            'tags': tags,
            'pmids': pmids,
            'date': date_created.strftime('%Y-%m-%d'),
            'datetime': date_created,
            'source': filepath.parent.name,  # 'searches', 'study-of-day', etc.
            'frontmatter': frontmatter
        }
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None


def get_all_articles(limit=None, source=None):
    """Obtiene todos los artículos de la biblioteca."""
    articles = []
    
    # Directorios a escanear
    dirs_to_scan = []
    if source:
        dirs_to_scan = [LIBRARY_BASE / source]
    else:
        dirs_to_scan = [SEARCHES_DIR, STUDY_OF_DAY_DIR, MONITOR_DIR]
    
    for dir_path in dirs_to_scan:
        if dir_path.exists():
            for md_file in sorted(dir_path.glob('*.md'), key=lambda x: x.stat().st_mtime, reverse=True):
                article = parse_markdown_file(md_file)
                if article:
                    articles.append(article)
    
    # Ordenar por fecha (más reciente primero)
    articles.sort(key=lambda x: x['datetime'], reverse=True)
    
    if limit:
        articles = articles[:limit]
    
    return articles


def get_article(article_id):
    """Obtiene un artículo específico por ID (filename sin extensión)."""
    # Buscar en todos los directorios
    for dir_path in [SEARCHES_DIR, STUDY_OF_DAY_DIR, MONITOR_DIR]:
        filepath = dir_path / f"{article_id}.md"
        if filepath.exists():
            return parse_markdown_file(filepath)
    
    return None


def search_articles(query, limit=20):
    """Busca artículos por texto en título, contenido o tags."""
    if not query or len(query.strip()) < 2:
        return []
    
    query_lower = query.lower()
    articles = get_all_articles()
    results = []
    
    for article in articles:
        score = 0
        
        # Buscar en título (peso alto)
        if query_lower in article['title'].lower():
            score += 10
        
        # Buscar en contenido (peso medio)
        if query_lower in article['content'].lower():
            score += 5
        
        # Buscar en tags (peso alto)
        for tag in article['tags']:
            if query_lower in tag.lower():
                score += 8
        
        if score > 0:
            article['score'] = score
            results.append(article)
    
    # Ordenar por relevancia
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:limit]


def get_featured_article():
    """Obtiene el artículo destacado (más reciente o aleatorio)."""
    articles = get_all_articles(limit=1)
    return articles[0] if articles else None


def get_library_stats():
    """Obtiene estadísticas de la biblioteca."""
    total_articles = len(get_all_articles())
    
    # Contar por fuente
    searches_count = len([a for a in get_all_articles() if a['source'] == 'searches'])
    study_of_day_count = len([a for a in get_all_articles() if a['source'] == 'study-of-day'])
    
    return {
        'total_articles': total_articles,
        'searches_count': searches_count,
        'study_of_day_count': study_of_day_count
    }


if __name__ == '__main__':
    # Prueba
    print("Artículos en biblioteca:")
    for article in get_all_articles(limit=5):
        print(f"  - {article['date']}: {article['title'][:60]}...")
        print(f"    Tags: {', '.join(article['tags'])}")
        print(f"    PMIDs: {article['pmids']}")
        print()