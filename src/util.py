from flask import session
import random
import string
import time


class util:

    def __private_generate_id_string(self):
        alphabets = ''.join(random.choices(string.ascii_uppercase, k=4))
        digits = ''.join(random.choices(string.digits, k=4))
        return f"{alphabets}{digits}"

    def generate_quiz_id(self):
        """
        Generates a unique quiz ID consisting of 4 random alphabetic characters followed by 4 random numbers.

        :return: A unique quiz ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"QIZ-{string_id}"

    def generate_assessment_id(self):
        """
        Generates a unique quiz ID consisting of 4 random alphabetic characters followed by 4 random numbers.

        :return: A unique quiz ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"AST-{string_id}"

    def generate_submission_id(self):
        """
        Generates a unique quiz ID consisting of 4 random alphabetic characters followed by 4 random numbers.

        :return: A unique quiz ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"SUB-{string_id}"


    def generate_inquiry_id(self):
        """
        Generates a unique inquiry ID consisting of the prefix 'INQ-' followed by 4 random alphabetic characters
        and 4 random numbers.

        :return: A unique inquiry ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"INQ-{string_id}"


    def generate_feedback_id(self):
        """
        Generates a unique feedback ID consisting of the prefix 'FDB-' followed by 4 random alphabetic characters
        and 4 random numbers.

        :return: A unique feedback ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"FDB-{string_id}"


    def generate_user_id(self):
        """
        Generates a unique feedback ID consisting of the prefix 'FDB-' followed by 4 random alphabetic characters
        and 4 random numbers.

        :return: A unique feedback ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"USR-{string_id}"


    def generate_answer_id(self):
        """
        Generates a unique feedback ID consisting of the prefix 'FDB-' followed by 4 random alphabetic characters
        and 4 random numbers.

        :return: A unique feedback ID as a string.
        """
        string_id = self.__private_generate_id_string()
        return f"ANS-{string_id}"

    def get_user_id(self):

        if 'user_id' not in session:
            session['user_id'] = self.generate_user_id()
            session['user_id_creation_time'] = time.time()

        return session['user_id']