import argparse

apimas_description = """
API Modeling And Serving.

This utility manages the installed APIs on this node.
You can initialize, configure, and manage the current node as an APIMAS server.
You can list, add, remove, configure, and manage individual APIs.
"""

parser = argparse.ArgumentParser(
    description=apimas_description,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)


def main():
    import sys
    parsed = parser.parse_args(sys.argv)
