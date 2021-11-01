{ self }:
final: prev: {
  peerix = self.packages.${prev.system}.peerix;
}
