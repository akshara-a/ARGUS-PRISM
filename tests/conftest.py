"""Global test configuration and fixture setup."""

import os
import pytest
from dotenv import load_dotenv

# Ensure local .env is loaded before running any tests
load_dotenv()
