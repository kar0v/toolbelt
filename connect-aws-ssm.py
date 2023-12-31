import contextlib
import signal
import subprocess
import json
import argparse
import os

# Get the AWS profile from the environment variable AWS_PROFILE
# If it is not set, ask the user to provide it
parser = argparse.ArgumentParser(description="Provide your AWS profile")
parser.add_argument('--profile', help='AWS profile to use')
args = parser.parse_args()

if os.environ.get('AWS_PROFILE') == None and args.profile == None:
  print("Please provide your AWS profile either as an argument or as an environment variable.")
  print("Example: export AWS_PROFILE=your_profile")
  print("Example: python3 connect.py --profile your_profile")
  exit()

if args.profile == None:
  args.profile = os.environ.get('AWS_PROFILE')
if os.environ.get('AWS_PROFILE') == None:
  os.environ['AWS_PROFILE'] = args.profile

def get_ec2_instances():
    try:
        cmd = [
            "aws", "ec2", "describe-instances",
            "--filter", "Name=instance-state-name,Values=running",
            "--region", "eu-central-1",
            "--profile", args.profile,
            "--query", "Reservations[*].Instances[].{Id:InstanceId, Name:Tags[?Key=='Name'].Value|[0]} | sort_by(@, &Name)",
            "--output", "json"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None



def select_instance(instances):
    # Determine the maximum width for each column
    max_name_length = max(len(instance.get('Name', 'N/A')) for instance in instances)
    max_id_length = max(len(instance['Id']) for instance in instances)

    # Header
    print(f"{'#.':<3} {'Name':<{max_name_length}}   {'Instance ID':<{max_id_length}}")
    print("-" * (3 + max_name_length + max_id_length + 2))

    # Rows
    for i, instance in enumerate(instances):
        name = instance.get('Name', 'N/A')
        # print the instance name, left aligned, padded with spaces to the max_name_length with numbers 1-9 padded accordingly numbers should end with a dot .
        j=str(i+1)+"."
        print(f"{j:<3} {name:<{max_name_length}}   {instance['Id']:<{max_id_length}}")

    # limit the choice to the number of instances, allow q for quit and c for cancel, also allow keyboard interrupt to quit
    # while the choice is invalid, return to the prompt
    while True:
        try:
            choice = input(f"Choose an instance (1-{len(instances)}) or q to quit: ") 
        except KeyboardInterrupt: # catch Ctrl+C
            print("\nInterrupted by user")
            exit()
        except EOFError: # catch Ctrl+D
            print("\nInterrupted by user")
            exit()
        except Exception as e: # catch any other exception
            print(f"Error: {e}")
            exit()

        if choice in ["q", "Q"]:
            exit()
        try:
            choice = int(choice) # enforce integer choice within the range of instances
            if choice < 1 or choice > len(instances):
                raise ValueError
            break
        except ValueError:
            print("Invalid choice, please try again.")
    return instances[choice - 1]['Id']


@contextlib.contextmanager
def ignore_user_entered_signals():
    """
    Ignores user entered signals to avoid process getting killed.
    """
    signal_list = [signal.SIGINT, signal.SIGQUIT, signal.SIGTSTP]
    actual_signals = []
    for user_signal in signal_list:
        actual_signals.append(signal.signal(user_signal, signal.SIG_IGN))
    try:
        yield
    finally:
        for sig, user_signal in enumerate(signal_list):
            signal.signal(user_signal, actual_signals[sig])
            
def start_ssm_session(instance_id):
    try:
        with ignore_user_entered_signals():
            subprocess.run(["aws", "ssm", "start-session", "--target", instance_id])
    except KeyboardInterrupt: # catch Ctrl+C
        print("\nInterrupted by user")
        exit()
    except EOFError: # catch Ctrl+D
        print("\nInterrupted by user")
        exit()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

def main():
    instances = get_ec2_instances()
    if instances:
        instance_id = select_instance(instances)
        try:
            start_ssm_session(instance_id)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("No running instances found or an error occurred.")

if __name__ == "__main__":
    main()
