import json
import os
import sys
from jsonschema import validate, ValidationError
from pprint import pprint

def remove_markdown(text):
    import re
    # Remove markdown links
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove markdown images
    text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
    # Remove markdown headers
    text = re.sub(r'#+\s*(.*)', r'\1', text)
    # Remove markdown bold and italic
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)
    # Remove markdown inline code
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove markdown code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove markdown blockquotes
    text = re.sub(r'>\s*(.*)', r'\1', text)
    # Remove markdown horizontal rules
    text = re.sub(r'---', '', text)
    return text

def first_sentence(text):
    import re
    # Find the first sentence by looking for a period followed by a space or end of string
    match = re.search(r'[^.!?]*[.!?]', text)
    if match:
        return match.group(0).strip()
    else:
        return text  # Return the original text if no sentence is found

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

            if 'description' in template:
                template['description'] = remove_markdown(template['description'])

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
            
            if 'network' not in template:
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
                    # {"name": "traefik.http.routers.{}.rule".format(service_name), "value": "HostRegexp(`^{}\..*`)".format(service_name)},
                    {"name": "traefik.http.routers.{}.rule".format(service_name), "value": "Host(`{}".format(service_name)+'.{$TRAEFIK_INGRESS_DOMAIN}'+'`)'},

                    {"name": "traefik.http.routers.{}.entrypoints".format(service_name), "value": "https"},
                    {"name": "traefik.http.services.{}.loadbalancer.server.port".format(service_name), "value": service_port},
                    {"name": "traefik.http.routers.{}.tls".format(service_name), "value": "true"},
                    {"name": "traefik.http.routers.{}.tls.certresolver".format(service_name), "value": "default"},
                    {"name": "traefik.http.routers.{}.middlewares".format(service_name), "value": "traefik-forward-auth"}
                    
                ]

                mafl_labels_to_add = [
                    {"name": "mafl.enable", "value": "true"},
                    {"name": "mafl.title", "value": "{}".format(template.get('title', template.get('name', '')))},
                    {"name": "mafl.description", "value": "{}".format(first_sentence(remove_markdown(template['description'])))},
                    # {"name": "mafl.tag", "value": "{}".format(template['tag'])},
                    {"name": "mafl.link", "value": "https://{}".format(service_name) + '.{$TRAEFIK_INGRESS_DOMAIN}' },
                    {"name": "mafl.icon.wrap", "value": "true"},
                    {"name": "mafl.icon.color", "value": "#007acc"},
                    {"name": "mafl.status.enabled", "value": "true"},
                    {"name": "mafl.status.interval", "value": "60"}
                ]

                if 'categories' in template and template['categories']:
                    mafl_labels_to_add.extend([
                        {"name": "mafl.group", "value": "{}".format(template.get('categories', ['Services'])[0])}
                    ])
                else:
                    mafl_labels_to_add.extend([
                        {"name": "mafl.group", "value": "Services"}
                    ])
                    template['categories'] = ['Uncategorized Services']

                if 'logo' in template:
                    mafl_labels_to_add.extend([
                        {"name": "mafl.icon.url", "value": "{}".format(template.get('logo', ''))},
                    ])
                else:
                    mafl_labels_to_add.extend([
                        {"name": "mafl.icon.name", "value": "simple-icons:docker"}
                    ])

                labels_to_add.extend(mafl_labels_to_add)

                
                # pprint(labels_to_add)
                print("-" * 100)
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
