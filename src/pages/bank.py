from src.mongoio import MongoIO


class Bank:
    def __init__(self):
        self.data_directory = 'storage/bank'
        # Allowed category names (all in lowercase)
        self.allowed_categories = [
            'business', 'administration', 'finance',
            'science', 'medical', 'technology',
            'creativity', 'law', 'culture'
        ]

    def give_genre_ls(self, category):
        if category not in self.allowed_categories:
            return None

        raw_catmeta_ls = MongoIO().load_documents_by_genre(category)
        catmeta_ls = []
        for meta in raw_catmeta_ls:
            doc = {'doc_id': meta['meta']['doc_id'], 'sub_genre': meta['meta']['sub_genre'],
                   'title': meta['meta']['title'], 'question_count': meta['meta']['question_count'],
                   'general_info': meta['meta']['general_info'],
                   }

            date_str = meta['meta']['creation_date_human']
            doc['date'] = date_str.split(",")[0] + "," + date_str.split(",")[1]
            if 'input_information' in meta['meta'].keys():
                doc['level'] = meta['meta']['input_information']['submit_info']['level']
            catmeta_ls.append(doc)
        return catmeta_ls

    def give_allowed_categories(self):
        return self.allowed_categories
