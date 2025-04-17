from src.mongoio import MongoIO


class assessment:

    def __init__(self):
        self.mongoio = MongoIO()

    def load_assessment_data(self, assessment_id):
        assessmend_doc, _ = self.mongoio.load_assessment_document(assessment_id)
        assessment_info = assessmend_doc['assessment_info']
        advice_dict = assessmend_doc['advice_dict']
        eval_id = assessmend_doc['meta']['eval_id']
        quiz_meta_dict = self.mongoio.load_eval_document(eval_id, section='meta')
        overall_dict = {
            'title': quiz_meta_dict[0]['title'],
            'right_count': len(assessment_info['correct_qids']),
            'wrong_count': len(assessment_info['wrong_qids']),
            'unsure_count': len(assessment_info['dont_know_qids']),
            'question_count': len(assessment_info['correct_qids']) + len(assessment_info['wrong_qids']),
            'accuracy': assessment_info['accuracy'] * 100
        }

        # Create answer script sorted by question index
        answer_script = []

        # Process correct answers
        for correct in assessment_info['correct_ls']:
            answer_script.append({
                "question_index": correct["question_index"],
                "question": correct["question"],
                "user_answer": correct["correct_answer"],
                "correct_answer": correct["correct_answer"],
                "is_correct": True,
                "explanation": correct["explanation"],
                "flagged": correct['question_flag_info']['flagged'],
                "dont_know": correct['question_flag_info']['dont_know'],
            })

        # Process wrong answers
        for wrong in assessment_info['wrong_ls']:
            answer_script.append({
                "question_index": wrong["question_index"],
                "question": wrong["question"],
                "user_answer": wrong["user_answer"],
                "correct_answer": wrong["correct_answer"],
                "is_correct": False,
                "explanation": wrong["explanation"],
                "flagged": wrong['question_flag_info']['flagged'],
                "dont_know": wrong['question_flag_info']['dont_know'],
            })

        # Sort by question index
        answer_script = sorted(answer_script, key=lambda x: x["question_index"])

        return answer_script, advice_dict, overall_dict
