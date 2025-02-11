{ pkgs ? import <nixpkgs> {} }:
with pkgs.python3Packages;

pkgs.mkShell {
  propagatedBuildInputs = [ numpy pandas ];
}
