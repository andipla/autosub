from os.path import isdir
from os.path import isfile
from os.path import join
from os import listdir
import os
import datetime
import shutil

#Validators
val={'TaskStart'           :[IS_NOT_EMPTY(), CLEANUP(),
                             IS_DATETIME(format=T('%Y-%m-%d %H:%M'),
                             error_message='must be YYYY-MM-DD HH:MM!')],

     'TaskDeadline'        :[IS_NOT_EMPTY(), CLEANUP(),
                             IS_DATETIME(format=T('%Y-%m-%d %H:%M'),
                             error_message='must be YYYY-MM-DD HH:MM!')],

     'Score'               :[IS_NOT_EMPTY(), CLEANUP(),
                             IS_DECIMAL_IN_RANGE(minimum=1)],

     'TaskOperator'        :[IS_NOT_EMPTY(), CLEANUP(),
                             IS_EMAIL_LIST()],

     'TaskActive'          :[IS_NOT_EMPTY(), CLEANUP(),
                             IS_IN_SET(['0','1'])],

     # the following will be extra validated in __extra_validation
     'TaskName'            :[CLEANUP()],

     'GeneratorExecutable' :[CLEANUP()],

     'Language'            :[CLEANUP()],

     'TestExecutable'      :[CLEANUP()],

     'BackendInterfaceFile':[CLEANUP()],
    }

# takes parameter, automatic private
def __extra_validation(form):
    tasks_dir = course(GeneralConfig.ConfigItem=='tasks_dir').select(GeneralConfig.Content)[0].Content
    available_tasks , available_backend_interfaces = __task_system_entries()

    #validate TaskName existence
    if form.vars.TaskName not in available_tasks:
        form.errors.TaskName = 'task does not exist'
        return

    #validate Language
    available_languages = __available_languages(form.vars.TaskName)
    if form.vars.Language not in available_languages:
        form.errors.Language = "supported: " + " , ".join(available_languages)
        return

    #validate BackendInterfaceFile existence
    backend_interface_file = form.vars.BackendInterfaceFile

    if not backend_interface_file:
        pass
    else:
        if not backend_interface_file in available_backend_interfaces:
            form.errors.BackendInterFaceFile = "file does not exist!"
            return

    task_path = join(tasks_dir, form.vars.TaskName)
    #validate GeneratorExecutable
    full_path = join(task_path, form.vars.GeneratorExecutable)
    if not isfile(full_path):
        form.errors.GeneratorExecutable = "file does not exist!"
        return

    #validate TestExecutable
    full_path = join(task_path, form.vars.TestExecutable)
    if not isfile(full_path):
        form.errors.TestExecutable = "file does not exist!"
        return

def __task_system_entries():
    tasks_dir = course(GeneralConfig.ConfigItem=='tasks_dir').select(GeneralConfig.Content)[0].Content

    available_tasks = [""]
    available_backend_interfaces = [""]

    if isdir(tasks_dir):
        # only take subfolders not files of tasks_dir
        available_tasks = sorted([d for d in listdir(tasks_dir)
                          if isdir(os.path.join(tasks_dir, d))])

        if '_backend_interfaces' in available_tasks:
            # delete _backend_interfaces out of it
            available_tasks.remove('_backend_interfaces')
            available_backend_interfaces.extend(sorted(listdir(tasks_dir + "/_backend_interfaces")))
            if "support_files" in available_backend_interfaces:
                available_backend_interfaces.remove("support_files")

    return (available_tasks , available_backend_interfaces)

def __entries():
    rows=course().select(TaskConfiguration.ALL, orderby=TaskConfiguration.TaskNr)
    array=[]

    for row in rows:
        entry={'TaskNr'               :row.TaskNr,
               'TaskStart'            :row.TaskStart.strftime("%Y-%m-%d %H:%M"),
               'TaskDeadline'         :row.TaskDeadline.strftime("%Y-%m-%d %H:%M"),
               'TaskName'             :row.TaskName,
               'GeneratorExecutable'  :row.GeneratorExecutable,
               'Language'             :"" if not row.Language else row.Language,
               'TestExecutable'       :row.TestExecutable,
               'BackendInterfaceFile' :"" if not row.BackendInterfaceFile else row.BackendInterfaceFile,
               'Score'                :row.Score,
               'TaskOperator'         :row.TaskOperator,
               'TaskActive'           :"Yes" if row.TaskActive else "No"}
        array.append(entry)

    tasks_dir = course(GeneralConfig.ConfigItem=='tasks_dir').select(GeneralConfig.Content)[0].Content

    if not isdir(tasks_dir):
        num_found_tasks = "Invalid Path."
    else:
       available_tasks , available_backend_interfaces = __task_system_entries()
       num_found_tasks = str(len(available_tasks)) + " task(s) found."

    return dict(entries=array, tasks_dir = tasks_dir,
                num_found_tasks = num_found_tasks)

def __available_languages(task_name):
    tasks_dir = course(GeneralConfig.ConfigItem=='tasks_dir').select(GeneralConfig.Content)[0].Content

    templates_dir = join(tasks_dir, task_name, "templates", "task_description")

    # no task_description template dir --> return [""]
    if not isdir(templates_dir):
        return [""]

    template_prefix = "task_description_template_"
    template_format = ".tex"
    prefix_len = len(template_prefix)
    format_len = len(template_format)

    available_languages = [filename[prefix_len : -format_len] for filename in listdir(templates_dir)
                                if filename.startswith(template_prefix)]

    if not available_languages:
        return [""]

    return available_languages

@auth.requires_permission('view data')
def index():
    returnDict={}
    returnDict.update(__entries())
    return returnDict

@auth.requires_permission('edit data')
def newTask():
    returnDict={}
    returnDict.update(__entries())

    #find next task nr (max() does not work..)
    rows=course().select(TaskConfiguration.TaskNr,orderby=TaskConfiguration.TaskNr)
    if len(rows)==0 :
        newTaskNr=1
    else:
        newTaskNr=rows.last().TaskNr+1
    returnDict.update({'newTaskNr': newTaskNr})

    available_tasks , available_backend_interfaces = __task_system_entries()

    inputs = TD(newTaskNr,INPUT(_type='hidden',_name='TaskNr',_value=newTaskNr)),\
             TD(INPUT(_name='TaskStart', requires=val['TaskStart'],
                      _placeholder="YYYY-MM-DD HH:MM", _id = 'TaskStart')),\
             TD(INPUT(_name='TaskDeadline', requires=val['TaskDeadline'],
                      _placeholder="YYYY-MM-DD HH:MM",_id = 'TaskEnd')),\
             TD(SELECT(_name="TaskName", requires=val['TaskName'],
                       *available_tasks)),\
             TD(INPUT(_name='GeneratorExecutable', _value="generator.sh",
                      requires=val['GeneratorExecutable'])),\
             TD(INPUT(_name='Language',requires=val['Language'], _value="")),\
             TD(INPUT(_name='TestExecutable', requires=val['TestExecutable'],
                      _value="tester.sh")),\
             TD(SELECT(_name='BackendInterfaceFile', *available_backend_interfaces,
                       requires=val['BackendInterfaceFile'], _value="")),\
             TD(INPUT(_name='Score', requires=val['Score'], _value=1)),\
             TD(INPUT(_name='TaskOperator', requires=val['TaskOperator'],\
                      _placeholder="Email")),\
             TD(INPUT(_type='submit',_label='Save'))
    form=FORM(inputs)

    if(form.process(onvalidation=__extra_validation).accepted):
        #Set TaskActive based on the StartTime
        if(form.vars.TaskStart < datetime.datetime.now()):
            TaskActive = 1;
        else:
            TaskActive = 0;

        TaskConfiguration.insert(TaskNr               =form.vars.TaskNr,\
                                 TaskStart            =form.vars.TaskStart,\
                                 TaskDeadline         =form.vars.TaskDeadline,\
                                 TaskName             =form.vars.TaskName,\
                                 GeneratorExecutable  =form.vars.GeneratorExecutable,\
                                 Language             =form.vars.Language,\
                                 TestExecutable       =form.vars.TestExecutable,\
                                 BackendInterfaceFile =form.vars.BackendInterfaceFile,\
                                 Score                =form.vars.Score,\
                                 TaskOperator         =form.vars.TaskOperator,\
                                 TaskActive           =TaskActive)

        # add a entry in TaskStats
        TaskStats.insert(TaskId=form.vars.TaskNr,
                          NrSubmissions=0,
                          NrSuccessful=0)

        # clear all LastDones, as there was a new addidional task added
        semester.executesql("UPDATE Users SET LastDone = NULL")

        redirect(URL('index'))

    returnDict.update({'form':form})
    return returnDict

@auth.requires_permission('edit data')
def editTask():
    returnDict={}
    returnDict.update(__entries())

    TaskNr = int(request.vars['editTaskNr'])
    entry = returnDict['entries'][TaskNr-1]

    available_tasks , available_backend_interfaces = __task_system_entries()

    inputs = TD(TaskNr),\
             TD(INPUT(_name='TaskStart', _value=entry['TaskStart'],
                      requires=val['TaskStart'], _id ='TaskStart', )),\
             TD(INPUT(_name='TaskDeadline', _value=entry['TaskDeadline'],
                      requires=val['TaskDeadline'], _id = 'TaskEnd')),\
             TD(SELECT(_name="TaskName", value=entry['TaskName'],
                       requires=val['TaskName'], *available_tasks)),\
             TD(INPUT(_name='GeneratorExecutable',
                      _value=entry['GeneratorExecutable'],
                      requires=val['GeneratorExecutable'])),\
             TD(INPUT(_name='Language', _value=entry['Language'],
                      requires=val['Language'])),\
             TD(INPUT(_name='TestExecutable', _value=entry['TestExecutable'],
                      requires=val['TestExecutable'])),\
             TD(SELECT(_name='BackendInterfaceFile', *available_backend_interfaces,
                       value=entry['BackendInterfaceFile'],
                       requires=val['BackendInterfaceFile'])),\
             TD(INPUT(_name='Score',_value=entry['Score'],
                      requires=val['Score'])),\
             TD(INPUT(_name='TaskOperator', _value=entry['TaskOperator'],
                      requires=val['TaskOperator'], _placeholder="Email")),\
             TD(INPUT(_type='submit',_label='Save'))
    form = FORM(inputs)

    if(form.process(onvalidation=__extra_validation).accepted):
        #Set TaskActive based on the StartTime
        if(form.vars.TaskStart < datetime.datetime.now()):
            TaskActive = 1;
        else:
            TaskActive = 0;

        course(TaskConfiguration.TaskNr ==TaskNr).update(\
                    TaskStart            =form.vars.TaskStart,\
                    TaskDeadline         =form.vars.TaskDeadline,\
                    TaskName             =form.vars.TaskName,\
                    GeneratorExecutable  =form.vars.GeneratorExecutable,\
                    Language             =form.vars.Language,\
                    TestExecutable       =form.vars.TestExecutable,\
                    BackendInterfaceFile =form.vars.BackendInterfaceFile,\
                    Score                =form.vars.Score,\
                    TaskOperator         =form.vars.TaskOperator,\
                    TaskActive           =TaskActive)

        redirect(URL('index'))

    returnDict.update({'editTaskNr':TaskNr,'form':form})
    return returnDict

@auth.requires_permission('edit data')
def deleteTask():
    TaskNr = request.vars['TaskNr']

    ###########################
    # MOVE USERS TASK FOLDERS #
    ###########################
    row = course(TaskConfiguration.TaskNr==TaskNr).select(TaskConfiguration.TaskName).first()
    TaskName = row['TaskName']

    row = course(GeneralConfig.ConfigItem=='users_dir').select(GeneralConfig.ALL).first()
    usersDir = row.Content

    now = datetime.datetime.now()

    timestamp = now.strftime("%Y-%m-%d_%H:%M:%S")

    rows = semester.executesql("SELECT UserId FROM UserTasks WHERE TaskNr=?"
        ,placeholders=TaskNr, as_dict=True)

    for row in rows:
        UserId = row['UserId']

        srcSubDir = "{0}/Task{1}".format(UserId, TaskNr)
        srcAbsoluteDir = os.path.join(usersDir, srcSubDir)


        tgtSubDir = "{0}/deletedTasks/{1}_{2}"\
            .format(UserId, TaskName, timestamp)
        tgtAbsoluteDir = os.path.join(usersDir, tgtSubDir)

        if not os.path.exists(tgtAbsoluteDir):
            os.makedirs(tgtAbsoluteDir)

        shutil.move(srcAbsoluteDir, tgtAbsoluteDir)

    ###########################
    #  DELETE ENTRIES FROM DB #
    ###########################
    if course(TaskConfiguration.TaskNr==TaskNr).delete() :
        msg ='Task with number' + TaskNr + ' deleted'
    else:
        msg ='Deletion of Task with number ' + TaskNr + ' failed'

    # also delete the TaskStats entry
    semester(TaskStats.TaskId==TaskNr).delete()

    # also delete from SuccessfulTasks
    # This does not work, so use raw sql query:
    #semester(SuccessfulTasks.TaskNr==TaskNr).delete()
    semester.executesql("DELETE FROM SuccessfulTasks WHERE TaskNr=?"
        ,placeholders=TaskNr)

    # also delete all User <-> Task entries from UserTasks
    semester.executesql("DELETE FROM UserTasks WHERE TaskNr=?"
        ,placeholders=TaskNr)

    redirect(URL('index'))
