import docx
import nltk
import config
import json
import orm
import model
from orm import Base
from typing import List, Dict
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker, class_mapper
from flask import Blueprint, request, render_template, make_response, jsonify 

from technologies import cardamom_tokenise
from technologies import cardamom_postag

api = Blueprint('api', __name__, template_folder='templates')

orm.start_mappers()
engine = create_engine(config.get_postgres_uri())
Base.metadata.create_all(engine)
get_session = sessionmaker(bind=engine)


def serialise(model):
    columns = [c.key for c in class_mapper(model.__class__).columns]
    return dict((c, getattr(model, c)) for c in columns)


def serialise_data_model(model):
    return {k: v for k, v in model.__dict__.items() if not k.startswith("_")}


def get_tokens(file_id, objectify=False):
    session = get_session()
    annots = session.query(model.TokenModel).filter(model.TokenModel.uploaded_file_id == file_id).all()
    for idx, annotation in enumerate(annots):
        annotation.token_language
        annotation.pos_instance
    if objectify:
        return session, annots
    annotations = [{**serialise(annot),"token_language_id": annot.token_language.iso_code}\
                                    for annot in annots]
    session.close()
    return sorted(annotations, key=lambda a: a['start_index'])


def get_replaced_tokens(start, end, annotations):
    # fetch the saved tokens
    i = 0
    replace_tokens = []

    while i < len(annotations):
        # if the new start is greater than annotations start
        new_set = set(range(start, end))
        overlap_set = set(range(annotations[i]["start_index"], annotations[i]["end_index"]))

        if len(new_set & overlap_set) > 0:
            while i < len(annotations) and end > annotations[i]["end_index"]:
                replace_tokens.append(annotations[i])
                i = i + 1
            replace_tokens.append(annotations[i])
            break
        i = i + 1
    return replace_tokens


@api.route('/login_user', methods=["POST"])
def login_user() -> Dict:
    """
    User login route
    """
    # for now we are just checking if the user name exist
    # we also need to check for password
    user_data = request.form.get("user")
    password_data = request.form.get("password")
    session = get_session()
    user = session.query(model.UserModel).filter(model.UserModel.email == user_data).one_or_none()
    session.close()
    if user:
        return jsonify({"user": user.id})
    else:
        return jsonify({"user": None})


@api.route('/get_files/', methods=["GET"])
def get_all_files() -> List[model.UploadedFileModel]:
    """
    Get user files route
    """
    # for a user get all of their files
    user_id = request.args.get("user")
    session = get_session()
    user_data = session.query(model.UserModel).filter(model.UserModel.id == user_id).one_or_none()
    files_ = user_data.uploaded_files
    file_contents = [{"filename": file.name, "file_id": file.id, "content": file.content.replace("\\n", "\n"),
                      "lang_id": file.language_id} for file in files_]
    session.close()
    return jsonify({"file_contents": file_contents})


@api.route('/fileUpload', methods=['POST'])
def file_upload():
    """
    Uploading a file
    """
    session = get_session()
    if 'file' not in request.files:
        print('abort(400)') 
    uploaded_file = request.files["file"]
    name = uploaded_file.filename
    name, extension = name.split('.')
    user_id = request.form['user_id']
    iso_code = request.form['iso_code']

    lang = session.query(model.LanguageModel).filter(model.LanguageModel.iso_code == iso_code).one_or_none()
    if extension == 'txt':
        # upload a txt file
        uploaded_file = uploaded_file.read()
        content = uploaded_file.decode("utf-8") 
        new_file = model.UploadedFileModel(name = name, content = content, user_id = user_id, language_id = lang.id)
        session.add(new_file)
        session.commit()
        session.flush()
        content = cardamom_tokenise(content, iso_code=iso_code)
        response_body = {
            "data": content
        }
    elif extension == 'docx':
        # upload a docx file
        uploaded_file = docx.Document(uploaded_file)
        text = []
        content = ''
        for para in uploaded_file.paragraphs:
            text.append(para.text)
        content = '\n'.join(text)
        session.add(model.UploadedFileModel(name, content, user_id, lang.id))
        session.commit()
        session.flush()
        content = cardamom_tokenise(content, iso_code=iso_code)
        response_body = {
            "data": content
        }
    sessio.close()
    return response_body


@api.route('/annotations/<file_id>', methods=["GET"])
def get_annotations(file_id) -> model.UploadedFileModel:
    annotations = get_tokens(file_id)
    print(annotations)
    return jsonify({"annotations": annotations})


@api.route('/annotations', methods=["POST"])
def push_annotations():
    # assuming the annotations come as a list of dictionaries
    data = request.get_json()
    annotations, file_id = data.get('tokens'), data.get("file_id")
    session = get_session()
    
    file = session.query(model.UploadedFileModel).filter(model.UploadedFileModel.id == file_id).one_or_none()

    # Check for tokens to be deleted
    extracted_annotations = get_tokens(file_id, objectify=False)
    for annotation in annotations:
        replace_tokens = get_replaced_tokens(annotation["start_index"], annotation["end_index"], extracted_annotations)
        for token in replace_tokens:
            session.query(model.TokenModel).filter(model.TokenModel.id == token["id"]).delete() 

        new_annotation = model.TokenModel(
            reserved_token=True if annotation["type_"] == "manual" else False,
            start_index=annotation["start_index"],
            end_index=annotation["end_index"],
            token_language_id=file.language_id,
            type_=annotation["type_"],
            uploaded_file_id=file_id
        )
        session.add(new_annotation)
    session.commit()
    session.flush()
    session.close()

    ''' #todo 
        # implement the gaps in the backend, 
        # we need to think how to replace the existing gaps with the new created gaps
    extracted_annotations = get_gaps(file_id)
    for gap in gaps:
        replace_tokens = get_replaced_tokens(annotation["start_index"], annotation["end_index"], extracted_annotations)
        for token in replace_tokens:
            session.query(model.TokenModel).filter(model.TokenModel.id == token["id"]).delete() 

        new_annotation = model.TokenModel(
            reserved_token=True if annotation["type_"] == "manual" else False,
            start_index=annotation["start_index"],
            end_index=annotation["end_index"],
            token_language_id=file.language_id,
            type_=annotation["type_"],
            uploaded_file_id=file_id
        )
        session.add(new_annotation)
    session.commit()
    session.flush()
    '''

    response_body = {
            "response": "success"
        }
    return response_body


@api.route('/auto_tokenise', methods=["POST"])
def auto_tokenise():
    session = get_session()
    file_data = json.loads(request.form.get("file_data"))
    text = file_data['content'].replace("\r", "")
    lang_id = file_data['lang_id']
    uploaded_file_id = file_data['file_id']
    reserved_tokens = json.loads(request.form.get("reservedTokens"))
    resv_tks = []
    for token in reserved_tokens:
        tok_mod = model.TokenModel(reserved_token=True, start_index=token['start_index'],
                                   end_index=token['end_index'], token_language_id=lang_id, type_=token['type_'],
                                   uploaded_file_id=uploaded_file_id)
        resv_tks.append(serialise_data_model(tok_mod))
    
    lang = session.query(model.LanguageModel).filter(model.LanguageModel.id == lang_id).one_or_none()
    tokenised_text = cardamom_tokenise(text, iso_code=lang.iso_code, reserved_toks=resv_tks,
                                       uploaded_file_id=uploaded_file_id)
    tokenised_text = [serialise_data_model(token_model) for token_model in tokenised_text]
    sorted(tokenised_text, key=lambda a: a['start_index'])
    session.close()
    return {"annotations": tokenised_text}

@api.route('/pos_tag', methods=["POST"])
def push_postags():
    data = request.get_json()
    pos_tags = data.get('tags')
    session = get_session()
    for token_id in pos_tags:
        if pos_tags[token_id]["tag"] is None:
            continue 
        else:
            pos_instance = model.POSInstanceModel(token_id=int(token_id), tag=pos_tags[token_id]["tag"],
                                                  type_=pos_tags[token_id]["type_"])
            session.add(pos_instance)
            session.commit()
            session.flush()
            session.refresh(pos_instance)
            if pos_tags[token_id].get('features'):
                for f_key_val in pos_tags[token_id]['features']:
                    f_key = f_key_val["feature"]
                    f_val = f_key_val["value"]
                    session.add(model.POSFeaturesModel(posinstance_id=pos_instance.id, feature=f_key, value=f_val))
                    session.commit()
                    session.flush()
    response_body = {
            "response": "success"
        }
    session.close()
    return response_body


@api.route('pos_tag/<file_id>', methods=["GET"])
def get_postags(file_id):
    session, tokens = get_tokens(file_id, objectify=True)
    token_tags = {}
    for token in tokens:
        instances = token.pos_instance
        for instance in instances:
            features = instance.features
            tag_features = []
            for feature in features:
                tag_features.append({"feature": feature.feature, "value": feature.value})
            token_tags[token.id] = {"tag": instance.tag, "features": tag_features, "start_index": token.start_index,
                                    "type_": token.type_, "token_id": token.id}
    annotations = get_tokens(file_id)
    annotations = [{"pos_tags": [serialise(posInstance) for posInstance in tokens[idx].pos_instance], **annotation} for idx, annotation in enumerate(annotations)]
    session.close()
    return jsonify({"annotations": sorted(annotations, key=lambda a: a['start_index']), "tags": token_tags})

@api.route('/auto_tag', methods=["POST"])
def auto_tag():
    # extract the text
    session = get_session()
    file_data = json.loads(request.form.get('file_data'))
    file_id = file_data["file_id"]
    lang_id = file_data["lang_id"]
    file_obj = session.query(model.UploadedFileModel)\
                        .filter(model.UploadedFileModel.id == file_id).one_or_none()
    content = file_obj.content
    tokens = get_tokens(file_id)
    lang = session.query(model.LanguageModel).filter(model.LanguageModel.id == lang_id).one_or_none()
    print(tokens)
    print(content)
    for token_ in tokens:
        print(content[token_["start_index"]: token_["end_index"]])
    pos_tags = cardamom_postag(content, tokens, lang)
    pos_tags = [serialise_data_model(tags) for tags in pos_tags]
    session.close()
    return {"POS": pos_tags}
