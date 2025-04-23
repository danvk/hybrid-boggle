#include "symmetry.h"

std::string Symmetry::Canonicalize(const std::string& board) {
  std::vector<std::string> rots;
  if (!AllSymmetries(board, &rots)) return "";
  rots.push_back(board);
  sort(rots.begin(), rots.end());
  return rots[0];
}

bool Symmetry::AllSymmetries(
    const std::string& board, std::vector<std::string>* analogues
) {
  if (board.size() != w_ * h_) return false;
  analogues->clear();
  std::string bd;
  bd = FlipLeftRight(board);
  if (board != bd) analogues->push_back(bd);
  bd = FlipTopBottom(bd);
  if (board != bd) analogues->push_back(bd);
  bd = FlipLeftRight(bd);
  if (board != bd) analogues->push_back(bd);

  if (w_ == h_) {
    bd = Rotate90CW(board);
    if (board != bd) analogues->push_back(bd);
    bd = FlipLeftRight(bd);
    if (board != bd) analogues->push_back(bd);
    bd = FlipTopBottom(bd);
    if (board != bd) analogues->push_back(bd);
    bd = FlipLeftRight(bd);
    if (board != bd) analogues->push_back(bd);
  }

  analogues->erase(std::unique(analogues->begin(), analogues->end()), analogues->end());
  return true;
}

std::string Symmetry::FlipTopBottom(const std::string& bd) {
  if (bd.size() != w_ * h_) return "";
  std::string out(w_ * h_, ' ');
  for (int y = 0; y < h_; y++) {
    for (int x = 0; x < w_; x++) {
      out[Id(x, y)] = bd[Id(x, h_ - 1 - y)];
    }
  }
  return out;
}

std::string Symmetry::FlipLeftRight(const std::string& bd) {
  if (bd.size() != w_ * h_) return "";
  std::string out(w_ * h_, ' ');
  for (int x = 0; x < w_; x++) {
    for (int y = 0; y < h_; y++) {
      out[Id(x, y)] = bd[Id(w_ - 1 - x, y)];
    }
  }
  return out;
}

std::string Symmetry::Rotate90CW(const std::string& bd) {
  if (w_ != h_) return "";  // rotation only works for square boards!
  std::string out(w_ * h_, ' ');
  for (int x = 0; x < w_; x++) {
    for (int y = 0; y < h_; y++) {
      out[Id(w_ - 1 - y, x)] = bd[Id(x, y)];
    }
  }
  return out;
}
