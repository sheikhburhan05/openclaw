#!/usr/bin/env python3
"""Legacy CLI filename — forwards to ``linkedin_sales_nav_cli`` (same ``argv``)."""

import sys

from linkedin_sales_nav_cli import main

if __name__ == "__main__":
    sys.exit(main())
