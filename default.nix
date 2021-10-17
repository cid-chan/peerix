let
  sources = import ./nix/sources.nix {};
in
{ pkgs ? import sources.nixpkgs {},
  lib ? pkgs.lib,
  ... 
}:
let
  mach-nix = import sources.mach-nix {
    inherit pkgs;
  };
in
mach-nix.buildPythonApplication {
  name = "peerix";
  python = "python39";
  src = lib.cleanSource ./.;
  version = builtins.readFile ./VERSION;
  requirements = builtins.readFile ./requirements.txt;
  propagatedBuildInputs = with pkgs; [
    nix
    nix-serve
  ];
}
