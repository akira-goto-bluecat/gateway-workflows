# Copyright 2018 BlueCat Networks (USA) Inc. and its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# By: BlueCat Networks
# Date: 04-05-18
# Gateway Version: 18.6.1
# Description: Example Gateway workflows


"""
Add host record page
"""
# Various Flask framework items.
import os

from flask import url_for, redirect, render_template, flash, g, request, jsonify

from bluecat import route, util
from bluecat.constants import SelectiveDeploymentStatus
from bluecat.server_endpoints import get_result_template, empty_decorator
import config.default_config as config
from main_app import app
from .add_host_record_example_form import GenericFormTemplate


def module_path():
    """
    Get module path.

    :return:
    """
    return os.path.dirname(os.path.abspath(str(__file__)))

# The workflow name must be the first part of any endpoints defined in this file.
# If you break this rule, you will trip up on other people's endpoint names and
# chaos will ensue.
@route(app, '/add_host_record_example/add_host_record_example_endpoint')
@util.workflow_permission_required('add_host_record_example_page')
@util.exception_catcher
def add_host_record_example_add_host_record_example_page():
    """
    Renders the form the user would first see when selecting the workflow.

    :return:
    """
    form = GenericFormTemplate()
    # Remove this line if your workflow does not need to select a configuration
    return render_template(
        'add_host_record_example_page.html',
        form=form,
        text=util.get_text(module_path(), config.language),
        options=g.user.get_options()
    )


@route(app, '/add_host_record_example/form', methods=['POST'])
@util.workflow_permission_required('add_host_record_example_page')
@util.exception_catcher
def add_host_record_example_add_host_record_example_page_form():
    """
    Processes the final form after the user has input all the required data.

    :return:
    """
    # pylint: disable=broad-except
    form = GenericFormTemplate()
    form.configuration.choices = util.get_configurations(default_val=True)

    if form.validate_on_submit():
        ip4_address_list = []
        try:
            # Retrieve form attributes
            configuration = g.user.get_api().get_entity_by_id(form.configuration.data)
            view = configuration.get_view(request.form['view'])
            absolute_name = form.hostname.data + '.' + request.form['zone']
            ip4_address = request.form['ip4_address']
            ip4_address_list.append(ip4_address)

            # Add host Record
            host_record = view.add_host_record(absolute_name, ip4_address_list)

            # Put form processing code here
            g.user.logger.info('Success - Host (A) Record ' + host_record.get_property('absoluteName') +
                               ' added with Object ID: ' + util.safe_str(host_record.get_id()))
            flash('Success - Host (A) Record ' + host_record.get_property('absoluteName') + ' added with Object ID: ' +
                  util.safe_str(host_record.get_id()), 'succeed')

            # Perform Selective Deployment (RELATED Scope) on host record if checkbox is checked
            if form.deploy_now.data:
                entity_id_list = [host_record.get_id()]
                deploy_token = g.user.get_api().selective_deploy(entity_id_list)
                return render_template('add_host_record_example_page.html',
                                       form=form,
                                       status_token=deploy_token,
                                       text=util.get_text(module_path(), config.language),
                                       options=g.user.get_options())
            return redirect(url_for('add_host_record_exampleadd_host_record_example_add_host_record_example_page'))
        except Exception as e:
            flash(util.safe_str(e))
            # Log error and render workflow page
            g.user.logger.warning('%s' % util.safe_str(e), msg_type=g.user.logger.EXCEPTION)
            return render_template('add_host_record_example_page.html',
                                   form=form,
                                   text=util.get_text(module_path(), config.language),
                                   options=g.user.get_options())
    else:
        g.user.logger.info('Form data was not valid.')
        return render_template('add_host_record_example_page.html',
                               form=form,
                               text=util.get_text(module_path(), config.language),
                               options=g.user.get_options())


@route(app, '/add_host_record_example/get_deploy_status', methods=['POST'])
@util.rest_workflow_permission_required('add_host_record_example_page')
@util.rest_exception_catcher
def get_deploy_status():
    """
    Retrieves and updates deployment task status
    :return:
    """
    result = get_result_template()
    deploy_token = request.form['deploy_token']
    try:
        task_status = g.user.get_api().get_deployment_task_status(deploy_token)
        result['status'] = task_status['status']

        if task_status['status'] == SelectiveDeploymentStatus.FINISHED:
            deploy_errors = task_status['response']['errors']

            # Deployment failed
            if deploy_errors:
                result['data'] = "FAILED"
                result['message'] = deploy_errors
                raise Exception('Deployment Error: ' + str(deploy_errors))

            # Deployment succeeded
            elif task_status['response']['views']:
                task_result = task_status['response']['views'][0]['zones'][0]['records'][0]['result']
                result['data'] = task_result

            # Deployment finished with no changes
            else:
                result['data'] = 'FINISHED'

            g.user.logger.info('Deployment Task Status: ' + str(task_status))

        # Deployment queued/started
        else:
            result['data'] = task_status['status']
    # pylint: disable=broad-except
    except Exception as e:
        g.user.logger.warning(e)

    return jsonify(empty_decorator(result))
