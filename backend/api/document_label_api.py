from api import methods
from api.methods import JSONEncoder, set_user_document_label, update_user_document_label
from bson import ObjectId
from firebase_auth import get_email
from flask import Blueprint, request, make_response
from model.document import get_db_collection
from mongoDBInterface import get_col

document_label_api = Blueprint('document_label_api', __name__)


# Endpoint to allow adding of labels to a document
@document_label_api.route('/projects/<project_name>/documents/<document_id>/label', methods=['Post'])
def set_label_for_user(project_name, document_id):
    id_token = request.args.get('id_token')

    if id_token is None or id_token == "":
        response = {'message': "ID Token is not included with the request uri in args"}
        response = make_response(response)
        return response, 400

    requestor_email = get_email(id_token)

    if requestor_email is None:
        response = {'message': "ID Token has expired or is invalid"}
        response = make_response(response)
        return response, 400

    if 'label_id' in request.json:
        label_id = request.json['label_id']
    else:
        response = {'message': "Missing label"}
        response = make_response(response)
        return response, 400

    # get user obj
    user_col = get_db_collection(project_name, "users")
    requestor = user_col.find_one({'email': requestor_email, 'isContributor': True})
    if requestor is None:
        response = {'message': "You are not authorised to perform this action"}
        response = make_response(response)
        return response, 403

    # get label obj
    label_col = get_db_collection(project_name, "labels")
    label = label_col.find_one({'_id': ObjectId(label_id)})
    if label is None:
        response = {'message': "Invalid Label"}
        response = make_response(response)
        return response, 400

    col = get_db_collection(project_name, "documents")
    document = col.find_one({'_id': ObjectId(document_id)})

    # If labels are already the same, prevent any further changes
    if document['label_confirmed']:
        response = {'message': "Label already confirmed"}
        response = make_response(response)
        return response, 400

    # Check if other contributor has labelled document
    two_contributors_have_labelled = len(document['user_and_labels']) == 2
    label_is_confirmed = False
    if two_contributors_have_labelled:
        for item in document['user_and_labels']:
            # If label assignments match, set confirmed
            if item['email'] != requestor_email and item['label'] == ObjectId(label_id):
                label_is_confirmed = True
                # Update other contributor
                update_user_document_label(col, item['email'], document_id, label_id, label_is_confirmed)

    current_user_label = col.find_one(
        {'_id': ObjectId(document_id), "user_and_labels": {'$elemMatch': {"email": requestor_email}}})
    # if the label already exists for the user
    if current_user_label is not None:
        set_user_document_label(col, requestor_email, document_id, label_id, label_is_confirmed)
    else:
        # if the label assignment does not exist for the user
        update_user_document_label(col, requestor_email, document_id, label_id, label_is_confirmed)

    return '', 204

# TODO: Change this later? Needs to include label_confirmed/label as params
@document_label_api.route('/projects/<project_name>/documents/<document_id>/label-agreement', methods=['POST'])
def set_final_label_after_agreement(project_name, document_id):
    id_token = request.args.get('id_token')

    if id_token is None or id_token == "":
        response = {'message': "ID Token is not included with the request uri in args"}
        response = make_response(response)
        return response, 400

    requestor_email = get_email(id_token)

    if requestor_email is None:
        response = {'message': "ID Token has expired or is invalid"}
        response = make_response(response)
        return response, 400

    # get user obj
    user_col = get_db_collection(project_name, "users")
    requestor = user_col.find_one({'email': requestor_email, 'isContributor': True})
    if requestor is None:
        response = {'message': "You are not authorised to perform this action"}
        response = make_response(response)
        return response, 403

    if 'label_id' in request.json:
        label_id = request.json['label_id']
    else:
        response = {'message': "Missing label"}
        response = make_response(response)
        return response, 400

    label_col = get_db_collection(project_name, "labels")
    label = label_col.find_one({'_id': ObjectId(label_id)})
    if label is None:
        response = {'message': "Invalid Label"}
        response = make_response(response)
        return response, 400

    doc_col = get_db_collection(project_name, "documents")
    doc = doc_col.find_one({'_id': ObjectId(document_id)})
    # check for doc existing
    if doc is None:
        response = {'message': "Invalid Document"}
        response = make_response(response)
        return response, 400

    # check that doc is fully labelled
    if len(doc['user_and_labels']) < 2:
        response = {'message': "Labelling for document incomplete!"}
        response = make_response(response)
        return response, 400

    # check for labelling confirmed
    if doc['label_confirmed']:
        response = {'message': "Label already confirmed!"}
        response = make_response(response)
        return response, 400

    # Confirm label is final and set labels for users
    for user_label in doc['user_and_labels']:
        doc_col.update_one({'_id': ObjectId(document_id),
                            "user_and_labels": {'$elemMatch': {"email": user_label['email']}}},
                           {'$set': {
                               "user_and_labels.$.label": ObjectId(label_id),
                               "label_confirmed": True}
                           })

    return '', 200


@document_label_api.route('/projects/<project_name>/unlabelled/documents', methods=['Get'])
def get_unlabelled_document_ids(project_name):
    id_token = request.args.get('id_token')

    try:
        page = int(request.args.get('page'))
        page_size = int(request.args.get('page_size'))
    except (ValueError, TypeError):
        response = {'message': "page and page_size must be integers"}
        response = make_response(response)
        return response, 400

    if id_token is None or id_token == "":
        response = {'message': "ID Token is not included with the request uri in args"}
        response = make_response(response)
        return response, 400

    requestor_email = get_email(id_token)

    if requestor_email is None:
        response = {'message': "ID Token has expired or is invalid"}
        response = make_response(response)
        return response, 400

    users_col = get_col(project_name, "users")
    requestor = users_col.find_one({'email': requestor_email})
    if requestor is None:
        response = {'message': "You are not authorised to perform this action"}
        response = make_response(response)
        return response, 403

    col = get_db_collection(project_name, "documents")
    docs = col.find({"user_and_labels": {'$not': {'$elemMatch': {"email": requestor_email}}}}, {'_id': 0})
    docs_in_page = docs.skip(page * page_size).limit(page_size)

    count = docs.count()

    docs_dict = {'docs': list(docs_in_page),
                 'count': count}
    docs_json = JSONEncoder().encode(docs_dict)
    return docs_json, 200


# Returns the ids of documents that have conflicting labels
@document_label_api.route('/projects/<project_name>/conflicting/documents', methods=['Get'])
def get_conflicting_labels_document_ids(project_name):
    id_token = request.args.get('id_token')

    try:
        page = int(request.args.get('page'))
        page_size = int(request.args.get('page_size'))
    except (ValueError, TypeError):
        response = {'message': "page and page_size must be integers"}
        response = make_response(response)
        return response, 400

    if id_token is None or id_token == "":
        response = {'message': "ID Token is not included with the request uri in args"}
        response = make_response(response)
        return response, 400

    requestor_email = get_email(id_token)

    if requestor_email is None:
        response = {'message': "ID Token has expired or is invalid"}
        response = make_response(response)
        return response, 400

    users_col = get_col(project_name, "users")
    requestor = users_col.find_one({'email': requestor_email})
    if requestor is None:
        response = {'message': "You are not authorised to perform this action"}
        response = make_response(response)
        return response, 403

    conflicting_doc_ids = []

    # get all documents
    doc_col = get_db_collection(project_name, "documents")
    documents = doc_col.find(projection={'comments': 0})

    # Check if labels match
    for d in documents:
        # Find final label id
        user_and_labels = d['user_and_labels']

        if len(user_and_labels) > 1:
            final_label_id = user_and_labels[0]['label']
            for item in user_and_labels:
                # check that label is the same
                if item['label'] != final_label_id:
                    conflicting_doc_ids.append(ObjectId(d['_id']))
                    break

    # get documents that conflict
    query = {'_id': {'$in': conflicting_doc_ids}}
    projection = {'_id': 1}
    docs = doc_col.find(query, projection).skip(page * page_size).limit(page_size)

    docs_dict = {'docs': list(docs)}
    docs = JSONEncoder().encode(docs_dict)
    return docs, 200

# TODO:? do we need this for individual users too?
# This end point returns the IDs of documents for which the final label is not confirmed
@document_label_api.route('/projects/<project_name>/unconfirmed/documents', methods=['Get'])
def get_documents_with_unconfirmed_labels(project_name):
    id_token = request.args.get('id_token')

    try:
        page = int(request.args.get('page'))
        page_size = int(request.args.get('page_size'))
    except (ValueError, TypeError):
        response = {'message': "page and page_size must be integers"}
        response = make_response(response)
        return response, 400

    if id_token is None or id_token == "":
        response = {'message': "ID Token is not included with the request uri in args"}
        response = make_response(response)
        return response, 400

    requestor_email = get_email(id_token)
    if requestor_email is None:
        response = {'message': "ID Token has expired or is invalid"}
        response = make_response(response)
        return response, 400

    users_col = get_col(project_name, "users")
    requestor = users_col.find_one({'email': requestor_email})
    if requestor is None:
        response = {'message': "You are not authorised to perform this action"}
        response = make_response(response)
        return response, 403

    doc_col = get_db_collection(project_name, "documents")
    # get documents that are not confirmed (i.e not labelled by both contributors OR the labels are conflicting)
    docs = doc_col.find({'label_confirmed': False}, {'_id': 1}).skip(page * page_size).limit(page_size)

    docs_dict = {'docs': list(docs)}
    docs = JSONEncoder().encode(docs_dict)
    return docs, 200
