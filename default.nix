{ pkgs, lib, ... }:
let
  sources = import ./sources.nix {};
  mach-nix = import sources.mach-nix {
    inherit pkgs;
  };
in
mach-nix.buildPythonApplication {
  src = lib.cleanSource ./..;
}
