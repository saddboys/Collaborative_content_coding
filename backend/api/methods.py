import json
from bson import ObjectId

from mongoDBInterface import get_col


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


def add_project_to_user(user_email, project_name):
    user_col = get_col("users", "users")
    user_col.update_one({"email": user_email}, {"$push": {"projects": project_name}})


def remove_project_from_user(user_email, project_name):
    user_col = get_col("users", "users")
    user_col.update_one({"email": user_email}, {"$pull": {"projects": project_name}})


def remove_all_labels_of_user(user_email, project_name):
    document_col = get_col(project_name, "documents")
    document_col.update(
        {
            "user_and_labels": {
                "$elemMatch": {
                    "email": user_email
                }
            }
        },
        {
            "$pull": {
                "user_and_labels": {
                    "email": user_email
            }
        }})
