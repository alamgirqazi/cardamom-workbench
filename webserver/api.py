import orm
import docx
import nltk
import config
from orm import Base
from typing import List, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, class_mapper
from flask import Blueprint, request, render_template, jsonify 

from Tokeniser import cardamom_tokenise

nltk.download('punkt')

api = Blueprint('api', __name__,
                        template_folder='templates')

# orm.start_mappers()
engine = create_engine(config.get_postgres_uri())
Base.metadata.create_all(engine)
get_session = sessionmaker(bind=engine)


def serialise(model):
    columns = [c.key for c in class_mapper(model.__class__).columns]
    return dict((c, getattr(model, c)) for c in columns)


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
    user = session.query(orm.User).filter(orm.User.email==user_data).one_or_none()
    if user:
        return jsonify({"user": user.id})
    else:
        return jsonify({"user": None})

@api.route('/get_files/', methods=["GET"])
def get_all_files() -> List[orm.UploadedFile]:
    """
    Get user files route
    """
    # for a user get all of their files
    user_id = request.args.get("user")
    session = get_session()
    user_data = session.query(orm.User).filter(orm.User.id == user_id).one_or_none()
    files_ = user_data.uploaded_files
    file_contents = [{"filename": file.name, "file_id": file.id, "content": cardamom_tokenise(file.content, "english")} for file in files_]
    return  jsonify({"file_contents": file_contents})

@api.route('/fileUpload', methods = ['POST'])
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

    if extension == 'txt':
        # upload a txt file
        uploaded_file = uploaded_file.read()
        content = uploaded_file.decode("utf-8") 
        new_file = orm.UploadedFile(name = name, content = content, user_id = user_id)
        session.add(new_file)
        session.commit()
        session.flush()
        content = cardamom_tokenise(content,"english")
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
        session.add(orm.UploadedFile(name, content, user_id))
        session.commit()
        session.flush()
        content = cardamom_tokenise(content,"english")
        response_body = {
            "data": content
        }
    return response_body

@api.route('/annotations/<file_id>', methods=["GET"])
def get_annotations(file_id) -> orm.UploadedFile:
    print(file_id)
    session = get_session()
    annots = session.query(orm.Annotation).filter(orm.Annotation.uploaded_file_id==file_id).all()
    annotations = [serialise(annot) for annot in annots]
    return jsonify({"annotations": annotations})



