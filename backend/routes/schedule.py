from flask import Blueprint, jsonify, current_app, request
from path_provider import PathProvider
from pathlib import Path
import yaml

schedule_bp = Blueprint('schedule', __name__)

@schedule_bp.route('/schedule', methods=['GET'])
def get_all():
    args = current_app.config['CUSTOM_ARGS']
    path = PathProvider.get_jobs_file()

    # 2) Ensure directory & file exist
    try:
        # 2a) Create parent dir(s) if missing
        jobs_path = Path(path)
        jobs_path.parent.mkdir(parents=True, exist_ok=True)

        # 2b) If file is absent, initialize with an empty list
        if not jobs_path.exists():
            with jobs_path.open('w') as f:
                yaml.safe_dump([], f)
    except PermissionError as e:
        return jsonify(
            error=f"Permission denied creating path 'jobs_path': {e}",
            message="Permission denied"
        ), 403
    except OSError as e:
        return jsonify(
            error=f"Filesystem error initializing 'jobs_path': {e}"
        ), 500

    try:
        # 1) load YAML
        with open(path, 'r') as f:
            jobs = yaml.safe_load(f) or []

        # 2) normalize to list
        if not isinstance(jobs, list):
            jobs = []

        # 3) build simplified list
        simplified = []
        for job in jobs:
            entry = {
                "id":       job.get("id"),
                "trigger":  job.get("trigger"),
                "name":     job.get("kwargs", {}).get("name"),
            }

            trigger_args = job.get("trigger_args", {})
            entry["run_date"] = trigger_args.get("run_date")
            
            if job.get("trigger") == "interval":
                # include minutes for interval-type jobs
                entry["minutes"]  = trigger_args.get("minutes", 0)
                entry["hours"]  = trigger_args.get("hours", 0)
                entry["days"]  = trigger_args.get("days", 0)


            simplified.append(entry)

        # 4) return only the pared-down list
        return jsonify(simplified), 200

    except FileNotFoundError:
        return jsonify(message=f'The file {path} does not exist'), 404

    except yaml.YAMLError as e:
        return jsonify(message=f'Error parsing YAML: {e}'), 400

    except Exception as e:
        return jsonify(message=f'Error: {e}'), 500
    

@schedule_bp.route('/schedule', methods=['POST'])
def save():
    args = current_app.config['CUSTOM_ARGS']
    path = PathProvider.get_jobs_file()

    try:
        # 1. Parse incoming JSON
        new_sched = request.get_json()

        print(f"\n{new_sched}\n")
        
        if not new_sched or 'id' not in new_sched:
            return jsonify(message='No JSON received or missing "id"'), 400

        # 2. Load existing YAML schedules (or start empty)
        try:
            with open(path) as f:
                full_schedules = yaml.safe_load(f) or []
        except FileNotFoundError:
            full_schedules = []

        if not isinstance(full_schedules, list):
            return jsonify(message='Jobs file malformed (expected top-level list)'), 500

        # 3. Reconstruct the full job dict from simplified fields
        job_id = new_sched['id']
        trigger = new_sched.get('trigger')
        name    = new_sched.get('name')

        # add extension if not provided
        if not name.endswith('.yaml'):
            name += '.yaml'

        # Base skeleton; use existing action if present, else default to the ID

        full_job = {
            'id':          job_id,
            'trigger':     trigger,
            'trigger_args': {},
            'action':      'run_robot',
            'kwargs':      {'name': name}
        }

        # Populate trigger_args
        if trigger == 'date':
            full_job['trigger_args']['run_date'] = new_sched.get('run_date')
        elif trigger == 'interval':
            full_job['trigger_args']['minutes']  = int(new_sched.get('minutes', "0"))
            full_job['trigger_args']['hours']  = int(new_sched.get('hours', "0"))
            full_job['trigger_args']['days']  = int(new_sched.get('days', "0"))

        else:
            return jsonify(message=f'Unknown trigger type: {trigger}'), 400

        # 4. Replace or append in the list
        # Remove old entry with same ID if present
        filtered = [job for job in full_schedules if job.get('id') != job_id]
        filtered.append(full_job)

        # 5. Write back to YAML
        with open(path, 'w') as f:
            yaml.safe_dump(
                filtered,
                f,
                sort_keys=False,           # preserve the key order you set in dicts :contentReference[oaicite:0]{index=0}
                default_flow_style=False   # use block style for readability :contentReference[oaicite:1]{index=1}
            )

        return get_all() # return the new schedule list

    except yaml.YAMLError as e:
        return jsonify(message=f'YAML error: {e}'), 500
    except ValueError as e:
        return jsonify(message=f'Error parsing value: {e}'), 500
    except Exception as e:
        return jsonify(message=f'Error: {e}'), 500
    
@schedule_bp.route('/schedule/<schedule_id>', methods=['DELETE'])
def delete(schedule_id):
    args = current_app.config['CUSTOM_ARGS']
    path = PathProvider.get_jobs_file()

    try:
        # 1. Load existing schedules
        try:
            with open(path, 'r') as f:
                schedules = yaml.safe_load(f)
                if schedules is None:
                    schedules = []
                elif not isinstance(schedules, list):
                    return jsonify(message='Jobs file malformed (expected list)'), 500
        except FileNotFoundError:
            schedules = []

        # 2. Remove the matching schedule
        original_count = len(schedules)
        schedules = [s for s in schedules if s.get('id') != schedule_id]
        if len(schedules) == original_count:
            return jsonify(message=f'No schedule found with id {schedule_id}'), 404

        # 3. Write updated schedules back
        with open(path, 'w') as f:
            yaml.safe_dump(
                schedules,
                f,
                sort_keys=False,
                default_flow_style=False
            )

        return get_all() #retornar la nueva lista

    except Exception as e:
        return jsonify(message=f'Error: {str(e)}'), 500
    
