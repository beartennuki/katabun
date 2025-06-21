# src/sitemap_generator.py
from datetime import datetime
from src.mongoio import MongoIO
from src.pages.bank import Bank


class SitemapGenerator:
    """
    Dynamically generates a sitemap.xml file by fetching URLs
    from static routes and the dynamic quiz bank categories from MongoDB.
    """

    def __init__(self):
        self.mongoio = MongoIO()
        self.bank = Bank()
        self.base_url = "https://4urclass.app"

    def generate_sitemap(self) -> str:
        """
        Constructs the full sitemap.xml as a string.
        :return: A string containing the sitemap in XML format.
        """
        # Get the current date for the <lastmod> tag
        today = datetime.now().strftime('%Y-%m-%d')

        # List of static public-facing pages and their SEO priority
        static_pages = [
            {'loc': '/', 'priority': '1.0', 'changefreq': 'weekly'},
            {'loc': '/bank/', 'priority': '0.9', 'changefreq': 'weekly'},
            {'loc': '/about', 'priority': '0.7', 'changefreq': 'monthly'},
            {'loc': '/contact', 'priority': '0.6', 'changefreq': 'monthly'},
            {'loc': '/feedback', 'priority': '0.6', 'changefreq': 'monthly'},
            {'loc': '/tnc', 'priority': '0.3', 'changefreq': 'yearly'},
            {'loc': '/privacy-policy', 'priority': '0.3', 'changefreq': 'yearly'},
            {'loc': '/cookie-policy', 'priority': '0.3', 'changefreq': 'yearly'},
            {'loc': '/disclaimer', 'priority': '0.3', 'changefreq': 'yearly'},
        ]

        # Start the XML content
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        # Add static page URLs to the sitemap
        for page in static_pages:
            xml_content += '  <url>\n'
            xml_content += f'    <loc>{self.base_url}{page["loc"]}</loc>\n'
            xml_content += f'    <lastmod>{today}</lastmod>\n'
            xml_content += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
            xml_content += f'    <priority>{page["priority"]}</priority>\n'
            xml_content += '  </url>\n'

        # Dynamically add the quiz bank category pages
        categories = self.bank.give_allowed_categories()
        for category in categories:
            xml_content += '  <url>\n'
            xml_content += f'    <loc>{self.base_url}/bank/{category}</loc>\n'
            xml_content += f'    <lastmod>{today}</lastmod>\n'
            xml_content += '    <changefreq>weekly</changefreq>\n'
            xml_content += '    <priority>0.8</priority>\n'
            xml_content += '  </url>\n'

        # Close the XML urlset
        xml_content += '</urlset>\n'
        return xml_content