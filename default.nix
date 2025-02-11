{ pkgs ? import <nixpkgs> {} }:
with pkgs.python3Packages;

buildPythonPackage rec {
  name = "robin-hood-profit";
  src = ./.;
  propagatedBuildInputs = [ numpy pandas ];

  postInstall = ''
    mv -v $out/bin/robin-hood-profit.py $out/bin/robin-hood-profit
  '';

  preBuild = ''
    cat > setup.py << EOF
from setuptools import setup

with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
  name='robin-hood-profit',
  #packages=['someprogram'],
  version='0.1.0',
  #author='...',
  #description='...',
  install_requires=install_requires,
  scripts=[
    'robin-hood-profit.py',
  ],
  entry_points={
    # example: file some_module.py -> function main
    #'console_scripts': ['someprogram=some_module:main']
  },
)
EOF
  '';
}
