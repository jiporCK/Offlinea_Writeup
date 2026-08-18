<?php

$api_scraper = "http://127.0.0.1:5000/generate?";
$search_string = ".php";


function url_check($url_test) {
    $chrome_headers = [
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language: en-US,en;q=0.9",
    "Sec-Fetch-Dest: document",
    "Sec-Fetch-Mode: navigate",
    "Sec-Fetch-Site: none",
    "Sec-Fetch-User: ?1",
    "Upgrade-Insecure-Requests: 1",
    ];
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url_test);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $chrome_headers);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if ($http_code != 200) {
        return false;
    }
}
function no_way_trick_me($url) {
    $private_ranges = [
        '127.0.0.0/8',
        '10.0.0.0/8',     
        '172.17.0.0/12',
        '192.168.0.0/16',
        '0.0.0.0/8',
        '169.254.0.0/16',
        '::1/128',
        'fe80::/10'

    ];
    $info = parse_url($url);
    $host = strtolower($info['host']);
    $ip = gethostbyname($host);
    if($host === ''){
        return false;
    }
    if (url_check($url) === false){
        return false;
    }
    if (false !== filter_var($host, FILTER_VALIDATE_IP)) {
        if (false === filter_var($host, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE)) {
            return false;
        }
    }
    if (!in_array($info['scheme'], ['https', 'http'])) {
        return false;
    }
    if (preg_match('/[{}]/', $url)) {
        return false;
    }
    foreach ($private_ranges as $range) {
        if (ip_in_range($ip, $range)) {
            return false;
        }
    }
    return true;
}
function ip_in_range($ip, $range) {
    if (strpos($range, '/') === false) {
        return $ip === $range;
    }

    list($subnet, $netmask) = explode('/', $range, 2);

    $ip_bin = inet_pton($ip);
    $subnet_bin = inet_pton($subnet);

    if (!$ip_bin || !$subnet_bin) {
        return false;
    }

    // Convert netmask to a binary string
    $addr_len = strlen($ip_bin);
    $mask_bin = str_repeat(chr(0xff), (int)($netmask / 8));
    if ($netmask % 8 !== 0) {
        $mask_bin .= chr(0xff << (8 - ($netmask % 8)));
    }
    $mask_bin = str_pad($mask_bin, $addr_len, chr(0x00));

    return ($ip_bin & $mask_bin) === ($subnet_bin & $mask_bin);
}

if ($_SERVER["REQUEST_METHOD"] == "GET") {
    $urlunsanitized = $_GET['url'];
    if (!no_way_trick_me($urlunsanitized)) {
        header('location: /pdfs/no_way.pdf');
 	exit();
}
    $t = time();
    $final_url = $api_scraper.$_SERVER['QUERY_STRING']."&time=".$t;
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $final_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    $response = curl_exec($ch);
    
    if(curl_getinfo($ch, CURLINFO_HTTP_CODE) == 200){
        sleep(5);
        header('location: /pdfs/results-'.$t.'.pdf');
	exit();
    }
    else{
        header('location: /pdfs/no_way.pdf');
    exit();
    }
}    
else {
    die('Request politely using GET method only.');
}

?>
