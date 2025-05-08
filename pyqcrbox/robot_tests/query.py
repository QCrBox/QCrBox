import requests


def send_get_request(address, data={}, headers={"Content-Type": "application/json"}):
    print(address)
    base_url = "http://127.0.0.1:11000/api/"
    response = requests.get(base_url + address, json=data, headers=headers)
    print(response.json())


def send_post_request(address, data={}, headers={"Content-Type": "application/json"}):
    print(address)
    base_url = "http://127.0.0.1:11000/api/"
    response = requests.post(base_url + address, json=data, headers=headers)
    print(response.json())


send_get_request("calculations")
send_get_request("interactive-sessions")
send_get_request("data-files")
send_get_request("datasets")


# send_request(
#     "commands/interactive",
#     {
#         "application_slug": "olex2",
#         "application_version": "1.5-alpha",
#         "data_file_id": "qcrbox_df_0x00326ce8d93042ba8355a3f8e0f04c3f",
#     },
# )
