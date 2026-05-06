# Contributing to PyPlasmod

PyPlasmod is the Python SDK for [Plasmod](https://github.com/plasmod-io/plasmod), an open-source vector database project on GitHub. Growing along with the development of Plasmod, PyPlasmod is one of the most popular sub-projects of Plasmod. Until Sept. 10th, 2021, PyPlasmod has gained more than 300 stars on GitHub and attracted 40 contributors.

Many people interested in Plasmod start by using PyPlasmod as their first contact with Plasmod. PyPlasmod 1.x, which is compatible with Plasmod 1.x, is a long-term support (LTS) version. PyPlasmod 2.x is compatible with Plasmod 2.x, and is now under active development.

Projects in the Plasmod community all welcome your contributions, and we welcome you to help build this community. PyPlasmod differs from other projects of Plasmod community because:

- It is a pure Python project;
- It supports Plasmod E2E, Benchmark, and Plasmod Bootcamp;
- It supports significantly more application scenarios as a Python package.

We are committed to building a collaborative, exuberant open-source community for PyPlasmod. Therefore, contributions to PyPlasmod are welcome from everyone. Anyone who is familiar with the code and usage of PyPlasmod is welcome to contribute to the community, help newcomers, and pass on the open-source, collaborative, and open spirit.


## What contributions can you make?

Issues with label [good-first-issue](https://github.com/plasmod-io/pyplasmod/labels/good%20first%20issue) and [help-wanted](https://github.com/plasmod-io/pyplasmod/labels/help%20wanted) in this repo are entry-level issues. They are the perfect starting points if you are trying to get familiar with this project.

If you want to challenge yourself, you may wish to look for issues with the label [Hacktoberfest](https://github.com/plasmod-io/pyplasmod/labels/Hacktoberfest).

If you identify any problems, you can:
1. [File an issue](https://github.com/plasmod-io/pyplasmod/issues/new/choose) to report the problem;
2. Describe how to reproduce this problem (optional);
3. Provide any possible solutions to this problem (optional);
4. Submit a Pull Request (PR) to solve this problem (optional).

If you are interested in existing problems, you can:
- Answer questions to offer help in issues with [question](https://github.com/plasmod-io/pyplasmod/labels/Issue%20%7C%20question) labels;
- In issues with [bug](https://github.com/plasmod-io/pyplasmod/labels/kind%2Fbug), [enhancement](https://github.com/plasmod-io/pyplasmod/labels/enhancement) labels:
  - Provide details on the problem, reproducing steps, and solutions;
  - Submit a PR to tackle the problem.

If you want to request more features for PyPlasmod, you can:
- [File an issue](https://github.com/plasmod-io/pyplasmod/issues/new/choose) to to describe the new features and explain why;
- Provide implementation design and test design (optional);
- Submit a PR to implement the feature (optional).

If you are interested in existing PRs, you can:
- Review the code and offer advice;
- Instruct new contributors to complete the PR process.

Note: the problems, features, and questions mentioned here are not limited to Python code. They also refer to all kinds of documents (technical documents, API references, contributing guide, etc.)

## PyPlasmod Code Structure
`docs/`: Contains PyPlasmod design and planning documents, such as `docs/plans`.

`examples/`: Contains Python scripts, which can be run directly, for introducing the usage of PyMiluvs API through examples.

`pyplasmod/`: Contains PyPlasmod source codes.

`tests/`: Contains unit tests.

`CONTRIBUTING.md`: Contributing guidelines.

`CONTRIBUTING_CN.md`: Contributing guidelines in Chinese.

`LICENSE`: Open Source License that PyPlasmod follows.

`Makefile`: Scripts for Github action.

`OWNERS`: This file designates reviewers and approvers for the current directory. They are chosen according to their participation and code contribution. Active contributors are listed as reviewers, responsible for code reviews. Reviewers who have been active and reviewing codes for a period of time are listed as approvers. They are in charge of reviewing content apart from codes. If you submit a PR and do not know who can help you review the code, you can assign reviewers and approvers from this file to review your PR.

`README.md`: Readme.

`requirements.txt`: Dependencies for developing PyPlasmod.

`setup.py`: Package script for PyPlasmod.

## Backporting (Cherry-pick)

We use a bot to automate backporting bug fixes to  branches.

**How to use:**
Simply add a label `backport-to-<branch-name>` to your Pull Request (e.g., `backport-to-2.6`).
* ✅ **Success**: The bot will create a new backport PR automatically.
* ❌ **Failure**: The bot will comment on your PR if there are conflicts or restricted files (`proto_gen/`).

If the bot fails due to conflicts, please backport manually.

## Congratulations! You are now the contributor to the Plasmod community!

Apart from dealing with codes and machines, you are always welcome to communicate with any member from the Plasmod community. New faces join us every day, and they may as well encounter the same challenges as you faced beore. Feel free to help them. You can pass on the collaborative spirit from the assistance you acquired when you first joined the community. Let us build a collaborative, open-source, exuberant, and tolerant community together!
