import os
from logging.config import dictConfig

from flask import jsonify
from flask_ask import Ask, question, session

from autobot_helpers import context_helper
from controllers.aws_api import aws_api
from controllers.nosession_api import nosession_api
from controllers.public_api import public_api
from flask_extended import Flask

os.environ['ROOT_PATH'] = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__)
app.config.from_yaml(os.path.join(app.root_path, 'config.yml'))
app.register_blueprint(aws_api, url_prefix='/api/v1/aws')
app.register_blueprint(nosession_api, url_prefix='/api/v1')
app.register_blueprint(public_api, url_prefix='/api/v1/public')
ask = Ask(app, "/")
dictConfig(app.config['LOGGER_CONFIG'])


def init_local():
    pass


def init():
    context_helper.initialize()


@ask.launch
def launch():
    init_local()
    init()
    return question("Hello, what can I do for you?")


@app.route('/getSetupProgress', methods=['GET'])
def get_setup_progress():
    return jsonify(
        {"cspSetup": True, "regionSet": True, "dataFetched": True, "tagResources": True, "assistantLinked": False})


@app.route('/cloudServiceProvider/checkAccess', methods=['POST'])
def csp_check_access():
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True)


def lambda_handler(event, _context):
    return ask.run_aws_lambda(event)
