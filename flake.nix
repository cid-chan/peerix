{
  description = "Peer2Peer Nix-Binary-Cache";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-compat = {
      url = "github:edolstra/flake-compat";
      flake = false;
    };
    flake-utils.url = "github:numtide/flake-utils";
    mach-nix = {
      url = "github:DavHau/mach-nix";
      inputs = {
        nixpkgs.follows = "nixpkgs";
        flake-utils.follows = "flake-utils";
      };
    };
  };

  outputs = { self, nixpkgs, flake-utils, mach-nix, ... }: {
    nixosModules.peerix = import ./module.nix;
    overlay = import ./overlay.nix { inherit self; };
  } // flake-utils.lib.eachDefaultSystem (system:
    let pkgs = nixpkgs.legacyPackages.${system}; in {
    packages.peerix = mach-nix.lib.${system}.buildPythonApplication {
      pname = "peerix";
      python = "python39";
      src = ./.;
      version = builtins.replaceStrings [ " " "\n" ] [ "" "" ] (builtins.readFile ./VERSION);
      requirements = builtins.readFile ./requirements.txt;
      propagatedBuildInputs = with pkgs; [
        nix
        nix-serve
      ];
    };

    defaultPackage = self.packages.${system}.peerix;

    devShell = pkgs.mkShell {
      buildInputs = with pkgs; [
        nix-serve
        niv
        (mach-nix.lib.${system}.mkPython {
          python = "python39";
          requirements = ''
            ${builtins.readFile ./requirements.txt}
            ipython
          '';
        })
      ];
    };

    defaultApp = { type = "app"; program = "${self.packages.${system}.peerix}/bin/peerix"; };
  });
}
