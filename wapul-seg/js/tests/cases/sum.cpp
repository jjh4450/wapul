#include <iostream>
#include <vector>
using namespace std;

int gcd(int a, int b) {
    if (b == 0) return a;
    return gcd(b, a % b);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n;
    cin >> n;
    vector<int> v(n);
    for (int i = 0; i < n; i++) {
        cin >> v[i];
    }
    long long sum = 0;
    int g = v[0];
    for (int x : v) {
        sum += x;
        g = gcd(g, x);
    }
    if (sum % 2 == 0) {
        cout << "even" << '\n';
    } else {
        cout << "odd" << '\n';
    }
    // 최대공약수
    cout << sum << ' ' << g << endl;
    return 0;
}
