def number_to_words(n):
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
            'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def two_digit(num):
        if num < 20:
            return ones[num]
        return tens[num // 10] + (' ' + ones[num % 10] if num % 10 else '')

    def three_digit(num):
        if num >= 100:
            return ones[num // 100] + ' Hundred' + (' ' + two_digit(num % 100) if num % 100 else '')
        return two_digit(num)

    if n == 0:
        return 'Zero'

    n = int(n)
    crore, n = divmod(n, 10000000)
    lakh, n = divmod(n, 100000)
    thousand, hundred = divmod(n, 1000)

    parts = []
    if crore:
        parts.append(three_digit(crore) + ' Crore')
    if lakh:
        parts.append(three_digit(lakh) + ' Lakh')
    if thousand:
        parts.append(three_digit(thousand) + ' Thousand')
    if hundred:
        parts.append(three_digit(hundred))

    return ' '.join(parts) if parts else 'Zero'


def amount_in_words(amount):
    return f"{number_to_words(int(amount))} Rupees Only".upper()