import os
import glob
import re

directory = r"e:\TSA\khushboo jewellers\khushboo jewellers\backend\templates"
html_files = glob.glob(os.path.join(directory, "*.html"))

mega_menu_html = """
                        <a href="/#collections" class="nav-link">Collections</a>
                        <div class="mega-menu" id="megaMenu">
                            <div class="mega-menu-content" id="megaMenuContent">
                                <div style="text-align: center; color: #999; padding: 20px;">Loading collections...</div>
                            </div>
                        </div>"""

for f in html_files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Check if the block is already there
    if '<li class="has-mega-menu">' in content and 'id="megaMenuContent"' not in content:
        pattern = r'(<li class="has-mega-menu">\s*)<a [^>]+>Collections</a>'
        content = re.sub(pattern, r'\1' + mega_menu_html, content)
        print(f"Updated mega menu html in {os.path.basename(f)}")

    # Add script tag before </body>
    if '/js/mega-menu-data.js' not in content:
        content = content.replace('</body>', '    <script src="/js/mega-menu-data.js"></script>\n</body>')
        print(f"Added script tag to {os.path.basename(f)}")
        
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

print("Done")
