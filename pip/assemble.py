#!/usr/bin/env python3

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import argparse
import glob
import os
import re
import shutil
import tempfile
from setuptools.sandbox import run_setup


parser = argparse.ArgumentParser()
parser.add_argument('--output_sdist', help="Output archive")
parser.add_argument('--output_wheel', help="Output archive")
parser.add_argument('--setup_py', help="setup.py")
parser.add_argument('--requirements_file', help="install_requires")
parser.add_argument('--readme', help="README file")
parser.add_argument('--files', nargs='+', help='Python files to pack into archive')
parser.add_argument('--data_files', nargs='+', default=[], help='Data files to pack into archive')
parser.add_argument('--imports', nargs='+', help='Folders considered to be source code roots')

args = parser.parse_args()

# absolutize the path
args.output_sdist = os.path.abspath(args.output_sdist)
args.output_wheel = os.path.abspath(args.output_wheel)
# turn imports into regex patterns
args.imports = list(map(
    lambda imp: re.compile('(?:.*){}[/]?(?P<fn>.*)'.format(imp)),
    args.imports or []
))

# new package root
pkg_dir = tempfile.mkdtemp()

if not args.files:
    raise Exception("Cannot create an archive without any files")

for f in args.files + args.data_files:
    fn = f
    for _imp in args.imports:
        match = _imp.match(fn)
        if match:
            fn = match.group('fn')
            break
    try:
        e = os.path.join(pkg_dir, os.path.dirname(fn))
        os.makedirs(e)
    except OSError:
        # directory already exists
        pass
    shutil.copy(f, os.path.join(pkg_dir, fn))

# MANIFEST.in is needed for data files that are not included in version control
if args.data_files:
    manifest_in_path = os.path.join(pkg_dir, 'MANIFEST.in')
    with open(manifest_in_path, 'w') as manifest_in:
        for f in args.data_files:
            manifest_in.write("include {}\n".format(f))

setup_py = os.path.join(pkg_dir, 'setup.py')
readme = os.path.join(pkg_dir, 'README.md')

with open(args.setup_py) as setup_py_template:
    install_requires = []
    with open(args.requirements_file) as requirements_file:
        for line in requirements_file.readlines():
            if not line.startswith('#') and not line.startswith('--') and line.strip() != '':
                install_requires.append(line.strip())
    with open(setup_py, 'w') as setup_py_file:
        setup_py_file.write(
            setup_py_template.read().replace("INSTALL_REQUIRES_PLACEHOLDER", str(install_requires))
        )

shutil.copy(args.readme, readme)

with open(os.path.join(pkg_dir, 'setup.cfg'), 'w') as setup_cfg:
    setup_cfg.writelines([
        '[bdist_wheel]\n',
        'universal = 1\n'
    ])

# change directory into new package root
os.chdir(pkg_dir)

# pack sources
run_setup(setup_py, ['sdist', 'bdist_wheel'])

sdist_archives = glob.glob('dist/*.tar.gz')
if len(sdist_archives) != 1:
    raise Exception('archive expected was not produced by sdist')

wheel_archives = glob.glob('dist/*.whl')
if len(wheel_archives) != 1:
    raise Exception('archive expected was not produced by bdist_wheel')

shutil.copy(sdist_archives[0], args.output_sdist)
shutil.copy(wheel_archives[0], args.output_wheel)
shutil.rmtree(pkg_dir)
