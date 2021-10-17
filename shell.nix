let
  sources = import ./nix/sources.nix {};
in
{ pkgs ? import sources.nixpkgs {} }:
let
  mach-nix = import sources.mach-nix {
    inherit pkgs;
  };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    nix-serve
    niv
    (mach-nix.mkPython {
      python = "python39";
      requirements = (builtins.readFile ./requirements.txt) + "\nipython";
    })
  ];
}
