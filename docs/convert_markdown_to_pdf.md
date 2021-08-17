# Install Pandoc on ubuntu
```
sudo apt install pandoc texlive-latex-recommended texlive-xetex texlive-luatex pandoc-citeproc etoolbox wkhtmltopdf
```

# WITH EISVOGEL
```
pandoc --number-sections --listings -H auto_linebreak_listings.tex \
    --variable papersize=a4paper --variable urlcolor=cyan \
    --toc -V toc-title:"Table of Contents" --variable papersize=a4paper \
    -s PebbleCounts_Manual_md.md -o PebbleCounts_Manual.pdf \
    --template eisvogel
```

# On Windows...

```
pandoc --number-sections --listings -H auto_linebreak_listings.tex --variable papersize=a4paper --variable urlcolor=cyan --toc -V toc-title:"Table of Contents" --variable papersize=a4paper -s PebbleCounts_Manual_md.md -o PebbleCounts_Manual.pdf --template C:\Users\BenPurinton\AppData\Roaming\pandoc\templates\eisvogel
```

## Breaks hyperlinks! Don't Use:
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook -dNOPAUSE -dQUIET -dBATCH -sOutputFile=PebbleCounts_Manual_ebook.pdf PebbleCounts_Manual_${d}.pdf
gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/printer -dNOPAUSE -dQUIET -dBATCH -sOutputFile=PebbleCounts_Manual.pdf PebbleCounts_Manual_${d}.pdf
rm -fr PebbleCounts_Manual_${d}.pdf
