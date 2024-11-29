import boto3
import json
import subprocess

ec2_client = boto3.client('ec2', region_name='eu-central-1')
running_instances = ec2_client.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
)

# This converts the dict to a string with the correct indentation, so it can be parsed.
json_data = json.dumps(running_instances, default=str, indent=4)
parsed_data = json.loads(json_data)  # load data in json


# This function checks if a key exists, if not it returns None.
# Useful, as the key 'Tags' is not always present
def check_for_key_error(instance, key):
    try:
        return instance[key]
    except KeyError:
        return None


def get_available_instances_in_region():
    instances_dict = {}
    for reservation in parsed_data['Reservations']:
        for instance in reservation['Instances']:
            tags = check_for_key_error(instance, 'Tags')
            instance_id = instance['InstanceId']
            if tags is not None:
                for tag in tags:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        instances_dict[instance_id] = instance_name
                        break
            else:
                instances_dict[instance_id] = 'Unnamed'
    return instances_dict


def select_instance(instances):
    instances_sorted = sorted(instances.items(), key=lambda kv: (kv[1], kv[0]))
    # Determine the maximum width for each column
    max_name_length = max(len(instance[1]) for instance in instances_sorted)
    max_id_length = max(len(instance[0]) for instance in instances_sorted)

    # Header
    print(f"{'#':<3} {'Name':<{max_name_length}}   {
          'Instance ID':<{max_id_length}}")
    print("-" * (7 + max_name_length + max_id_length))

    # Rows
    for i, instance in enumerate(instances_sorted):
        name = instance[1]
        j = str(i+1)+"."
        print(f"{j:<3} {name:<{max_name_length}}   {
              instance[0]:<{max_id_length}}")

    # Footer
    print("-" * (7 + max_name_length + max_id_length))

    while True:
        try:
            choice = input(
                f"Choose an instance (1-{len(instances)}) or q to quit: ")
        except KeyboardInterrupt:  # catch Ctrl+C
            print("\nGoodbye!\n")
            exit()
        except EOFError:  # catch Ctrl+D
            print("\nGoodbye!\n")
            exit()
        except Exception as e:  # catch any other exception
            print(f"Error: {e}")
            exit()

        if choice in ["q", "Q"]:
            print("Goodbye!\n")
            exit()
        try:
            # enforce integer choice within the range of instances
            choice = int(choice)
            if choice < 1 or choice > len(instances):
                raise ValueError
            break
        except ValueError:
            print("Invalid choice, please try again.")

    return instances_sorted[choice - 1][0]


def start_ssm_session(instance_id):
    try:
        # Start the session using the AWS CLI
        subprocess.run(
            ['aws', 'ssm', 'start-session', '--target', instance_id])
    except KeyboardInterrupt:  # catch Ctrl+C
        print("\nInterrupted by user")
        exit()
    except EOFError:  # catch Ctrl+D
        print("\nInterrupted by user")
        exit()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        exit()

def main():
    selected_instance = select_instance(get_available_instances_in_region())
    start_ssm_session(selected_instance)


if __name__ == "__main__":
    main()
