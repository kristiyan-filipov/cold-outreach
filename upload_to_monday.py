import requests
import json
import os

GRAPHQL_URL = "https://api.monday.com/v2"
FILE_UPLOAD_URL = "https://api.monday.com/v2/file"

def create_item_with_update_and_files(api_key, board_id, group_id, item_name, update_text, file_paths):
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    create_item_query = """
    mutation CreateItem($board_id: ID!, $group_id: String, $item_name: String!, $position_relative_method: PositionRelative) {
      create_item(
        board_id: $board_id,
        group_id: $group_id,
        item_name: $item_name,
        position_relative_method: $position_relative_method
      ) {
        id
        name
      }
    }
    """
    variables_create = {
        "board_id": board_id,
        "group_id": group_id,
        "item_name": item_name,
        "position_relative_method": "after_at"
    }

    response_create = requests.post(
        GRAPHQL_URL,
        headers=headers,
        json={"query": create_item_query, "variables": variables_create}
    )
    response_data = response_create.json()
    print("Create Item Response:")
    print(json.dumps(response_data, indent=2))

    item_id = response_data.get("data", {}).get("create_item", {}).get("id")
    if not item_id:
        print("Failed to create item.")
        return None

    add_update_query = """
    mutation AddUpdate($item_id: ID!, $body: String!) {
      create_update(item_id: $item_id, body: $body) {
        id
        body
      }
    }
    """
    variables_update = {
        "item_id": int(item_id),
        "body": update_text
    }
    response_update = requests.post(
        GRAPHQL_URL,
        headers=headers,
        json={"query": add_update_query, "variables": variables_update}
    )
    response_update_data = response_update.json()
    print("Add Update Response:")
    print(json.dumps(response_update_data, indent=2))

    update_id = response_update_data.get("data", {}).get("create_update", {}).get("id")
    if not update_id:
        print("Failed to create update.")
        return None

    def upload_file_to_update(update_id, file_path):
        if not os.path.isfile(file_path):
            print(f"File does not exist: {file_path}")
            return

        mutation = """
        mutation ($file: File!) {
          add_file_to_update(update_id: %d, file: $file) {
            id
          }
        }
        """ % int(update_id)

        variables = {"file": None}
        map_ = {"file": ["variables.file"]}

        with open(file_path, "rb") as f:
            files = {
                'query': (None, mutation),
                'variables': (None, json.dumps(variables)),
                'map': (None, json.dumps(map_)),
                'file': (os.path.basename(file_path), f, 'application/octet-stream')
            }
            headers_no_content_type = {"Authorization": api_key}

            response = requests.post(FILE_UPLOAD_URL, headers=headers_no_content_type, files=files)

        if response.status_code == 200:
            print(f"Uploaded file '{file_path}' to update {update_id}.")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Failed to upload file '{file_path}'. Status: {response.status_code}")
            print(response.text)

    if file_paths:
        for path in file_paths:
            upload_file_to_update(update_id, path)
    else:
        print("No files to upload.")

    return item_id, update_id
