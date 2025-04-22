from firebase_admin import credentials, firestore, auth, initialize_app
from kivy.app import App

class FirebaseManager:
    _instance = None
    
    def __init__(self):
        if not FirebaseManager._instance:
            self.cred = credentials.Certificate("serviceAccountKey_exemple.json")
            self.app = initialize_app(self.cred, {
                'databaseURL': 'https://SEU_PROJECT.firebaseio.com',
                'projectId': 'SEU_PROJECT_ID'
            })
            self.db = firestore.client()
            self.auth = auth
            FirebaseManager._instance = self

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = FirebaseManager()
        return cls._instance

    @classmethod
    def _initialize_in_thread(cls):
        cls._instance = FirebaseManager()

    def get_user_id(self):
        user = App.get_running_app().current_user
        return user.uid if user else None