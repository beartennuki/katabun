
import os
import json
class localio():

    def __init__(self):

        main_dir = 'storage'
        submission_path = os.path.join(main_dir, 'submission')
        respond_path = os.path.join(main_dir, 'respond')
        self.cache_path = os.path.join(main_dir, 'temp')

        self.quiz_submission = os.path.join(submission_path, 'quiz')
        self.assessment_submission = os.path.join(submission_path, 'assessment')

        self.quiz_respond = os.path.join(respond_path, 'quiz')
        self.assessment_respond = os.path.join(respond_path, 'assessment')

        paths = [
            main_dir,
            submission_path,
            respond_path,
            self.cache_path,
            self.quiz_submission,
            self.assessment_submission,
            self.quiz_respond,
            self.assessment_respond
        ]
        for path in paths:
            if not os.path.exists(path):
                os.mkdir(path)
                print(f'New path has been generated: {path}')

    def __dump_json(self, path, data):
        with open(path,'w') as file:
            json.dump(data, file, indent=4)
            print(f'Dummped data at: {path}')

    def __load_json(self,path):
        with open(path, 'r') as file:
            data = json.load(file)
        return data

    def save_autoquiz_submission(self, data, id):
        path = os.path.join(self.quiz_submission, id)
        self.__dump_json(path, data)

    def save_assessment_cache(self, data, id):
        path = os.path.join(self.cache_path, id)
        self.__dump_json(path, data)

    def load_assessment_cache(self, id):
        path = os.path.join(self.cache_path, id)
        data = self.__load_json(path)
        return data