# Data Harvester Agent
# Lazy import to avoid RuntimeWarning when running via `python -m agents.harvester.harvester_agent`.
# The `python -m` runner imports this package first, then runs the module as __main__.
# An eager import here causes the module to be registered twice in sys.modules.
def __getattr__(name):
    if name == "DataHarvesterAgent":
        from agents.harvester.harvester_agent import DataHarvesterAgent
        return DataHarvesterAgent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
