# coding=utf-8
import hashlib
import os
from subprocess import Popen, PIPE

import arrow
import yaml
from bottle import route, run, auth_basic, redirect, response

PROJECTS_FOLDER = 'projects'
BUILD_ARCHIVE_FOLDER = 'builds'
SOURCE_FOLDER = 'source'
CONFIG_FILE = 'config.yaml'
BUILD_NUMBER_FILE = '.lastbuildnumber'
USERS_FILE = 'users'
TIMEZONE = 'Europe/Istanbul'


def check_and_create_folder(path):
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise Exception('Folder not exists / cannot be created.')
    else:
        os.mkdir(path)


def run_cmd(cmd, cwd=None):
    process = Popen(cmd, shell=True, stdout=PIPE, stdin=PIPE, stderr=PIPE, cwd=cwd)
    output = process.communicate()
    return process.returncode, '> ' + cmd + '\n' + '\n'.join(output)


def run_multi_cmd(commands, cwd=None):
    code = 0
    total_output = ''

    for cmd in commands:
        code, output = run_cmd(cmd, cwd)
        total_output += output + '\n'
        if code != 0:
            break
    if code != 0:
        total_output += '\nreturn code ' + str(code) + '\nFAILURE'
    else:
        total_output += '\nSUCCESS'
    return code, total_output


def deploy(project):
    project_folder = PROJECTS_FOLDER + '/' + project + '/'
    if not os.path.isdir(project_folder):
        raise Exception('Project not found.')

    build_archive_path = project_folder + BUILD_ARCHIVE_FOLDER + '/'
    check_and_create_folder(build_archive_path)
    build_number_file_path = project_folder + '/' + BUILD_NUMBER_FILE
    with open(build_number_file_path, 'a+') as f:
        f.seek(0)
        build_number = f.read()
        if not build_number:
            f.write('0')
        f.seek(0)
        build_number = int(f.read())

    project_source_path = project_folder + SOURCE_FOLDER + '/'
    check_and_create_folder(project_source_path)

    config_file_path = PROJECTS_FOLDER + '/' + project + '/' + CONFIG_FILE
    if not os.path.exists(config_file_path):
        raise Exception('Config file not found.')

    config = yaml.load(open(config_file_path, 'r'))
    try:
        git_url = config['git']['url']
        git_branch = config['git'].get('branch', 'master')
        target_folder = config['target']
        ignore_files = config.get('ignore', [])
    except BaseException as ex:
        raise Exception('Error reading config file: ' + str(ex.message))

    if not os.path.isdir(target_folder):
        raise Exception('Target folder not found.')

    # build copy files command
    sync_cmd = "rsync -rcvh --delete --exclude='.git*' "
    for ignored_file in ignore_files:
        sync_cmd += "--exclude='" + ignored_file.replace("'", "\'") + "' "
    sync_cmd += '. ' + target_folder

    if os.path.exists(project_source_path + '.git'):
        code, output = run_multi_cmd([
            'git fetch -v',
            # TODO: accept host authenticity check question automatically.
            'git checkout ' + git_branch,
            'git pull -v',
            sync_cmd
        ], project_source_path)
    else:
        code, output = run_multi_cmd([
            'git init',
            'git remote -v add origin ' + git_url,
            'git fetch -v',
            # TODO: accept host authenticity check question automatically.
            'git checkout ' + git_branch,
            sync_cmd
        ], project_source_path)

    build_number += 1

    with open(build_number_file_path, 'w+') as f:
        f.seek(0)
        f.write(str(build_number))

    with open(build_archive_path + str(build_number), 'w+') as f:
        f.seek(0)
        f.write(output)

    # TODO: add fail and success hooks based on code.

    return code != 0, build_number


def check_pass(username, password):
    # TODO: make a less shittier login check.
    users = {}
    with open('users', 'r') as f:
        content = f.read().split('\n')
        for u in content:
            if not u: continue
            u = u.split(',')
            users[u[0]] = u[1]

    pass_hash = users.get(username)
    if not pass_hash:
        return False

    m = hashlib.md5()
    m.update(password)
    if pass_hash != m.hexdigest():
        return False

    return True


header = """<style>
* { font-family: monospace; white-space: pre; }
a:hover { color: gray; }
</style>"""


@route('/')
@auth_basic(check_pass)
def index():
    html = header
    html += '<h1>Projects</h1>'
    for project in next(os.walk(PROJECTS_FOLDER))[1]:
        html += '<a href="projects/' + project + '">' + project + '</a>\n'
    return html


def get_file_time(file_path):
    return arrow.get(os.path.getmtime(file_path)).to(TIMEZONE).format('YYYY-MM-DD HH:mm:ss')


@route('/projects/<project>')
@auth_basic(check_pass)
def project_summary(project):
    html = header
    html += '<h1>' + project + '</h1>'
    deploy_trigger_url = PROJECTS_FOLDER + '/' + project + '/deploy'
    html += '<a href="/' + deploy_trigger_url + '">Trigger Build</a>'
    builds_folder = PROJECTS_FOLDER + '/' + project + '/builds/'
    html += '<h2>Builds</h2>'
    if not os.path.isdir(builds_folder):
        os.mkdir(builds_folder)
    for build in sorted([int(x) for x in os.listdir(builds_folder)], reverse=True)[0:100]:
        build = str(build)
        created_time = get_file_time(builds_folder + build)
        html += '<a href="/' + builds_folder + build + '">#' + build.rjust(10) + '</a> / ' + created_time + '\n'
    return html


@route('/projects/<project>/builds/<build_number>')
@auth_basic(check_pass)
def build_report(project, build_number):
    project_path = PROJECTS_FOLDER + '/' + project
    build_file_path = project_path + '/builds/' + build_number
    html = header
    html += '<h1><a href="/' + project_path + '">' + project + '</a> / ' + \
            'Build #' + build_number + ' / ' + \
            get_file_time(build_file_path) + '</h1>'
    with open(build_file_path, 'r') as f:
        html += f.read()
    return html


@route('/projects/<project>/deploy', ['GET', 'POST'])
@auth_basic(check_pass)
def deploy_project(project):
    try:
        result, build_number = deploy(project)
    except BaseException as ex:
        import traceback
        traceback.print_exc()
        response.status = 400
        return ex.message
    build_result_url = '/' + PROJECTS_FOLDER + '/' + project + '/builds/' + str(build_number)
    redirect(build_result_url, 302)


run(host='0.0.0.0', port=8080)
