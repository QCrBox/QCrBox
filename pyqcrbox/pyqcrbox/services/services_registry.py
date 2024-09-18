import svcs


class DevelopmentServicesRegistry(svcs.Registry):
    def __init__(self):
        super().__init__()


def get_qcrbox_services_registry():
    # For now, we're just using the development registry. In the future,
    # we may want to use different registries for different environments
    # (e.g., development, testing, production).
    return DevelopmentServicesRegistry()



QCRBOX_GLOBAL_SERVICES_REGISTRY = get_qcrbox_services_registry()
