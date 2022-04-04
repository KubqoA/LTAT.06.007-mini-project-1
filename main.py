import sys


if __name__=='__main__':
  # Check for correctness of provided arguments
  if len(sys.argv) != 2 or not sys.argv[1].isdigit():
    print("Usage: %s [number_of_processes]" % sys.argv[0], file=sys.stderr)
    sys.exit(1)

  n = int(sys.argv[1])
  print("Launching %d processes" % n)
