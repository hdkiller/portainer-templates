import json
import os
import sys
from jsonschema import validate, ValidationError
from pprint import pprint

def load_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

def main():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))

        templates_file = os.path.join(script_dir, '..', 'templates.json')

        templates = load_json_file(templates_file)
        templates_with_labels = { 
            "version": "2",
            "templates": []
        }

        for template in templates.get('templates', []):
            if 'volumes' in template and template['volumes']:
                for volume in template['volumes']:
                    if 'bind' in volume:
                        volume['bind'] = volume['bind'].replace('/portainer/Files/AppData/Config/', '/opt/appdata/').lower()
                        volume['bind'] = volume['bind'].replace('/volume1/docker/', '/opt/appdata/').lower()

            # If there is only one volume, and the bind is ends with /config, remove the /config from the container
            if 'volumes' in template and len(template['volumes']) == 1 and 'bind' in template['volumes'][0] and template['volumes'][0]['bind'].endswith('/config'):
                template['volumes'][0]['bind'] = template['volumes'][0]['bind'].replace('/config', '')

            if 'network' in template and template['network'] != 'bridge':
                template['network'] = 'web'
            if 'ports' in template and template['ports'] and 'name' in template:
                # try to find the service port
                for port in template['ports']:
                    if ':' in port:
                        port_protocol = port.split(':')[1].split('/')[1] if '/' in port.split(':')[1] else 'tcp'
                        if port_protocol == 'tcp':
                            service_port = port.split(':')[1].split('/')[0]
                            break

                service_name = ''.join(e for e in template['name'].lower() if e.isalnum() or e in ['-', '_', '.'])
                
                labels_to_add = [
                    {"name": "traefik.enable", "value": "true"},
                    {"name": "traefik.http.routers.{}.rule".format(service_name), "value": "HostRegexp(`^{}\..*`)".format(service_name)},
                    {"name": "traefik.http.routers.{}.entrypoints".format(service_name), "value": "https"},
                    {"name": "traefik.http.services.{}.loadbalancer.server.port".format(service_name), "value": service_port},
                    {"name": "traefik.http.routers.{}.tls".format(service_name), "value": "true"},
                    {"name": "traefik.http.routers.{}.tls.certresolver".format(service_name), "value": "default"},
                    {"name": "traefik.http.routers.{}.middlewares".format(service_name), "value": "traefik-forward-auth"}
                ]
                if 'labels' not in template:
                    template['labels'] = []
                for label in labels_to_add:
                    existing_label = next((l for l in template['labels'] if l['name'] == label['name']), None)
                    if existing_label:
                        existing_label['value'] = label['value']
                    else:
                        template['labels'].append(label)
                pprint(template)
            
            templates_with_labels['templates'].append(template)
        
        
        with open(os.path.join(script_dir, '..', 'templates_with_labels.json'), 'w') as file:
            json.dump(templates_with_labels, file, indent=4)
    except Exception as e:
        print("Error: ", e.message)

if __name__ == '__main__':
    main()
