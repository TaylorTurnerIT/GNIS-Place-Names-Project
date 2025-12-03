AGENTS.md: Python Code Style and Formatting Guide

This document provides instructions for AI agents to ensure all Python code in this repository adheres to PEP 8, PEP 257, and other standard community guidelines.

Your primary objective is to write clean, readable, and consistent Python code.

1. Core Philosophy: PEP 8

All Python code MUST follow the PEP 8 style guide. The official guide is your ultimate source of truth.

Key directives are summarized below.

1.1. Code Layout

Indentation: Use 4 spaces per indentation level. Do not use tabs.

Line Length: Limit all lines to a maximum of 79 characters.

Long Lines: For lines over 79 characters, use Python's-implied line continuation inside parentheses, brackets, and braces.

# Correct: Implied continuation
def my_long_function(
        param_one, param_two,
        param_three, param_four):
    return param_one + param_two


Blank Lines:

Use two blank lines to separate top-level function and class definitions.

Use one blank line to separate method definitions inside a class.

Use blank lines sparingly inside functions to separate logical steps.

1.2. Whitespace

Operators: Surround binary operators with a single space on either side (=, +=, ==, !=, >, <, and, or, in).

# Correct
x = y + 1
if x > 5 and y in my_list:
    ...


Function Arguments: Use a single space after commas in argument lists. Do not put a space before the opening parenthesis of a function call.

# Correct
my_func(arg1, arg2, kwarg1=True)

# Incorrect
my_func ( arg1,arg2 , kwarg1 = True )


Containers: Do not include spaces immediately inside parentheses, brackets, or braces.

# Correct
my_list[0]

# Incorrect
my_list[ 0 ]


Trailing Whitespace: Remove all trailing whitespace from all lines.

2. Naming Conventions

Naming is critical for readability. Stick to these conventions universally.

Packages & Modules: lowercase_with_underscores (e.g., my_module.py)

Classes: CapitalizedWords (also known as PascalCase or CamelCase). (e.g., MyClass)

Functions & Methods: lowercase_with_underscores (e.g., my_function)

Variables: lowercase_with_underscores (e.g., my_variable)

Constants: UPPERCASE_WITH_UNDERSCORES (e.g., GLOBAL_CONSTANT)

Method Arguments:

First argument in an instance method: self

First argument in a class method: cls

Protected & Private:

Non-public (protected) methods/attributes: _single_leading_underscore

Name-mangled (private) attributes: __double_leading_underscore

3. PEP 257: Docstrings

All public modules, functions, classes, and methods MUST have docstrings.

Format: Use triple double-quotes ("""...""").

One-Line Docstrings: The closing """ is on the same line.

def my_simple_function():
    """This is a one-line docstring."""
    pass


Multi-Line Docstrings:

A short summary line (like a one-line docstring).

A blank line.

A more detailed description, including arguments, return values, and any exceptions raised.

The closing """ is on its own line.

def my_complex_function(arg1, arg2):
    """
    Summarize the function's purpose in one line.

    Provide a more detailed explanation of what the function
    does, its inputs, and its outputs.

    Args:
        arg1 (str): Description of the first argument.
        arg2 (int): Description of the second argument.

    Returns:
        bool: Description of the return value.
    """
    return True


4. Imports

Placement: All imports go at the top of the file, just after any module-level docstrings and comments.

One Per Line: Do not import multiple packages on the same line.

# Correct
import os
import sys

# Incorrect
import os, sys


Grouping & Order: Imports must be grouped in this order, with a blank line separating each group:

Standard library imports (e.g., os, sys, json)

Related third-party imports (e.g., pandas, requests)

Local application/library-specific imports (e.g., from . import my_other_module)

Absolute Imports: Prefer absolute imports (e.g., from my_package.utils import helper) over relative imports.

5. Comments

Block Comments: Indent to the same level as the code they describe. Each line must start with a # followed by a single space.

Inline Comments: Use them sparingly. Separate them from the code by at least two spaces. They must start with a # and a single space.

x = x + 1  # Increment x


"Why," not "What": Good comments explain why something is done, not what is being done (the code should explain what).

6. Tooling

Before finalizing any changes, you should format and lint the code using the project's standard tools.

Formatter: Run black . to automatically format all code.

Linter: Run flake8 . to check for any remaining PEP 8 violations or potential bugs.

Import Sorting: Run isort . to automatically sort all imports according to the rules in section 4.

Your goal is for all tools (black, isort, flake8) to pass without errors.

7. Project Structure

When adding new files, follow the existing project structure.

Source Code: New modules belong in the main source directory (e.g., src/ or project_name/).

Tests: New tests must be added to the tests/ directory and should mirror the source code's structure. All new functions and classes must have corresponding tests.

Dependencies: If you add a new third-party dependency, add it to the pyproject.toml or requirements.txt file.