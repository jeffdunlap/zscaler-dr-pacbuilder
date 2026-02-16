# zscaler-dr-pacbuilder
This is a python application that takes a text file of URLs (allow-list.txt) and uses the allow list to generate a perfectly formed proxy.pac file for Zscaler ZIA DR Mode.

### Column Name
- [ ] Add CI pipeline (GitHub Actions) for automated testing

### Completed Column ✓
- [x] Build todo.md file
- [x] Build python program to parse allow-list.txt and add the URLs into a templated proxy.pac file
- [x] Add a check to ensure the allow list entry is not already included on the zscaler allow list https://dll7xpq8c5ev0.cloudfront.net/drdb.txt
- [x] Build a method to test the proxy.pac file and test for syntax and to confirm that there are no issues
