from qcrbox_wrapper import QCrBoxPathHelper, QCrBoxWrapper

pathhelper = QCrBoxPathHelper.from_dotenv(".env.dev", "gui_folder/prototype0")

qcrbox = QCrBoxWrapper.from_server_addr("127.0.0.1", 11000)

print(qcrbox.application_dict)

