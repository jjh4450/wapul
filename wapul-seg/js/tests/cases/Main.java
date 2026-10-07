import java.io.*;
import java.util.*;

public class Main {
    static int[] memo = new int[100];

    static int fib(int k) {
        if (k < 2) return k;
        if (memo[k] != 0) return memo[k];
        memo[k] = fib(k - 1) + fib(k - 2);
        return memo[k];
    }

    public static void main(String[] args) throws IOException {
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        StringTokenizer st = new StringTokenizer(br.readLine());
        int t = Integer.parseInt(st.nextToken());
        StringBuilder sb = new StringBuilder();
        while (t-- > 0) {
            int k = Integer.parseInt(br.readLine().trim());
            switch (k % 3) {
                case 0:
                    sb.append("zero\n");
                    break;
                default:
                    sb.append(fib(k)).append('\n');
            }
        }
        System.out.print(sb);
    }
}
