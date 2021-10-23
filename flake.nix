{
  description = "Peer2Peer Nix-Binary-Cache";

  outputs = { self }: {
    nixosModules.peerix = import ./module.nix;
  };
}
