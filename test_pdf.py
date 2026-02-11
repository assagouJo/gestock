from weasyprint import HTML

HTML(string="<h1>OK</h1>").write_pdf("test.pdf")
print("PDF généré")
