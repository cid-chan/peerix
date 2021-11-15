{
  description = "Peer2Peer Nix-Binary-Cache";

  inputs = {
    nixpkgs.url = "nixpkgs/nixpkgs-unstable";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }: {
    nixosModules.peerix = import ./module.nix;
    overlay = import ./overlay.nix { inherit self; };
  } // flake-utils.lib.eachDefaultSystem (system:
    let
      pkgs = nixpkgs.legacyPackages.${system};
      python = pkgs.python39;
      packages = map (pkg: python.pkgs.${pkg}) (builtins.filter (v: builtins.isString v && (builtins.stringLength v) > 0) (builtins.split "\n" (builtins.readFile ./requirements.txt)));
    in {
      packages = rec {
        peerix-unwrapped = python.pkgs.buildPythonApplication {
          pname = "peerix";
          version = builtins.replaceStrings [ " " "\n" ] [ "" "" ] (builtins.readFile ./VERSION);
          src = ./.;

          doCheck = false;
    
          propagatedBuildInputs = with pkgs; [
            nix
            nix-serve
          ] ++ packages;
        };

        peerix = pkgs.writeShellScriptBin "peerix" ''
          PATH=${pkgs.nix}/bin:${pkgs.nix-serve}:$PATH
          exec ${peerix-unwrapped}/bin/peerix "$@"
        '';
      };

      defaultPackage = self.packages.${system}.peerix;

      devShell = pkgs.mkShell {
        buildInputs = with pkgs; [
          nix-serve
          niv
          (python.withPackages (ps: packages))
        ];
      };

      defaultApp = { type = "app"; program = "${self.packages.${system}.peerix}/bin/peerix"; };
    });
}
