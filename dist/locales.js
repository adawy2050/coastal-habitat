/* National-language interface labels. Dataset names and source titles are retained. */
(() => {
  const names={en:'English',ar:'العربية','zh-Hans':'简体中文','zh-Hant':'繁體中文',ja:'日本語',ko:'한국어',fil:'Filipino',id:'Bahasa Indonesia',ms:'Bahasa Melayu',vi:'Tiếng Việt',ru:'Русский',fa:'فارسی'};
  const rows=`Map|地図|地图|地圖|지도|Mapa|Peta|Peta|Bản đồ|Карта
Seasonal outlook|季節見通し|季节展望|季節展望|계절 전망|Tanaw sa susunod na panahon|Prakiraan musim|Tinjauan musim|Triển vọng theo mùa|Сезонный прогноз
Climate indices|気候指数|气候指数|氣候指數|기후 지수|Mga indeks ng klima|Indeks iklim|Indeks iklim|Chỉ số khí hậu|Климатические индексы
Habitat photographs|生息地の写真|生境照片|棲地照片|서식지 사진|Mga larawan ng tirahan|Foto habitat|Foto habitat|Ảnh sinh cảnh|Фотографии местообитаний
Research & news|研究とニュース|研究与新闻|研究與新聞|연구와 소식|Pananaliksik at balita|Riset dan berita|Kajian dan berita|Nghiên cứu và tin tức|Исследования и новости
Data & methods|データと方法|数据与方法|資料與方法|자료와 방법|Datos at pamamaraan|Data dan metode|Data dan kaedah|Dữ liệu và phương pháp|Данные и методы
Coastal Habitat Heatwave Atlas|沿岸生息地の海洋熱波アトラス|沿海生境海洋热浪图集|沿海棲地海洋熱浪圖集|연안 서식지 해양열파 지도집|Atlas ng Init sa mga Tirahang Baybayin|Atlas Gelombang Panas Habitat Pesisir|Atlas Gelombang Haba Habitat Pesisir|Bản đồ nắng nóng biển tại sinh cảnh ven bờ|Атлас морских волн тепла в прибрежных местообитаниях
Marine heatwaves in coastal habitats|沿岸生息地の海洋熱波|沿海生境的海洋热浪|沿海棲地的海洋熱浪|연안 서식지의 해양열파|Mga alon ng init sa mga tirahang baybayin|Gelombang panas laut di habitat pesisir|Gelombang haba laut di habitat pesisir|Nắng nóng biển tại sinh cảnh ven bờ|Морские волны тепла в прибрежных местообитаниях
Choose an area on the map|地図で範囲を選択|在地图上选择区域|在地圖上選擇區域|지도에서 영역 선택|Pumili ng lugar sa mapa|Pilih area pada peta|Pilih kawasan pada peta|Chọn vùng trên bản đồ|Выберите область на карте
Draw a rectangle|四角形で範囲を指定|绘制矩形|繪製矩形|사각형 그리기|Gumuhit ng parihaba|Gambar persegi panjang|Lukis segi empat|Vẽ hình chữ nhật|Нарисовать прямоугольник
Draw a rectangle, or choose a study area below. Then select a habitat cell.|四角形を描くか、下の海域を選び、生息地セルを選択してください。|绘制矩形或选择下方海域，然后选择生境网格。|繪製矩形或選擇下方海域，再選擇棲地網格。|사각형을 그리거나 아래 해역을 고른 뒤 서식지 격자를 선택하세요.|Gumuhit ng parihaba o pumili ng lugar sa ibaba. Pagkatapos, pumili ng selula ng tirahan.|Gambar persegi panjang atau pilih wilayah di bawah, lalu pilih sel habitat.|Lukis segi empat atau pilih kawasan di bawah, kemudian pilih sel habitat.|Vẽ hình chữ nhật hoặc chọn vùng bên dưới, rồi chọn ô sinh cảnh.|Нарисуйте прямоугольник или выберите район ниже, затем ячейку местообитания.
Use map view|表示範囲を使用|使用当前视图|使用目前視圖|현재 지도 범위 사용|Gamitin ang nakikitang mapa|Gunakan tampilan peta|Gunakan paparan peta|Dùng vùng bản đồ hiện tại|Использовать видимую область
Explore all areas|全海域を表示|浏览全部区域|瀏覽全部區域|모든 해역 보기|Tingnan ang lahat ng lugar|Jelajahi semua area|Teroka semua kawasan|Xem tất cả các vùng|Все районы
Choose another area|別の範囲を選択|选择其他区域|選擇其他區域|다른 영역 선택|Pumili ng ibang lugar|Pilih area lain|Pilih kawasan lain|Chọn vùng khác|Выбрать другую область
Clear rectangle|範囲選択を解除|清除矩形|清除矩形|영역 선택 해제|Alisin ang parihaba|Hapus persegi panjang|Padam segi empat|Xóa hình chữ nhật|Сбросить прямоугольник
Enter rectangle corners|範囲の座標を入力|输入矩形角点|輸入矩形角點|사각형 모서리 좌표 입력|Ilagay ang mga sulok|Masukkan sudut area|Masukkan bucu kawasan|Nhập các góc hình chữ nhật|Введите углы прямоугольника
Use rectangle|指定範囲を使用|使用矩形|使用矩形|사각형 영역 사용|Gamitin ang parihaba|Gunakan area|Gunakan kawasan|Dùng hình chữ nhật|Применить прямоугольник
South|南|南|南|남쪽|Timog|Selatan|Selatan|Nam|Юг
North|北|北|北|북쪽|Hilaga|Utara|Utara|Bắc|Север
West|西|西|西|서쪽|Kanluran|Barat|Barat|Tây|Запад
East|東|东|東|동쪽|Silangan|Timur|Timur|Đông|Восток
Study area|対象海域|研究区域|研究區域|연구 해역|Lugar ng pag-aaral|Wilayah kajian|Kawasan kajian|Vùng nghiên cứu|Район исследования
All study areas|全対象海域|全部研究区域|全部研究區域|모든 연구 해역|Lahat ng lugar|Semua wilayah|Semua kawasan|Tất cả vùng nghiên cứu|Все районы исследования
East Asia & western Pacific|東アジア・西太平洋|东亚与西太平洋|東亞與西太平洋|동아시아 및 서태평양|Silangang Asya at kanlurang Pasipiko|Asia Timur dan Pasifik barat|Asia Timur dan Pasifik barat|Đông Á và Tây Thái Bình Dương|Восточная Азия и западная часть Тихого океана
Red Sea & Gulf of Aden|紅海・アデン湾|红海与亚丁湾|紅海與亞丁灣|홍해 및 아덴만|Dagat Pula at Golpo ng Aden|Laut Merah dan Teluk Aden|Laut Merah dan Teluk Aden|Biển Đỏ và vịnh Aden|Красное море и Аденский залив
Arabian Gulf & Gulf of Oman|アラビア湾・オマーン湾|阿拉伯湾与阿曼湾|阿拉伯灣與阿曼灣|아라비아만 및 오만만|Golpo ng Arabia at Golpo ng Oman|Teluk Arab dan Teluk Oman|Teluk Arab dan Teluk Oman|Vịnh Ả Rập và vịnh Oman|Арабский залив и Оманский залив
Heatwaves through time|海洋熱波の経年変化|海洋热浪的时间变化|海洋熱浪的時間變化|해양열파의 시간 변화|Mga alon ng init sa paglipas ng panahon|Gelombang panas dari waktu ke waktu|Gelombang haba mengikut masa|Nắng nóng biển theo thời gian|Волны тепла во времени
Heatwave days by month and year|月別・年別の海洋熱波日数|各月各年热浪天数|各月各年熱浪天數|월별·연도별 해양열파 일수|Mga araw ng init ayon sa buwan at taon|Hari gelombang panas per bulan dan tahun|Hari gelombang haba mengikut bulan dan tahun|Số ngày nắng nóng biển theo tháng và năm|Дни волн тепла по месяцам и годам
Heatwave days|海洋熱波日数|热浪天数|熱浪天數|해양열파 일수|Mga araw ng init|Hari gelombang panas|Hari gelombang haba|Số ngày nắng nóng biển|Дни волн тепла
Event frequency|発生回数|事件频次|事件頻次|발생 횟수|Dalas ng pangyayari|Frekuensi kejadian|Kekerapan kejadian|Tần suất sự kiện|Частота событий
Mean event duration|平均継続日数|平均持续时间|平均持續時間|평균 지속 기간|Karaniwang tagal|Rata-rata durasi|Purata tempoh|Thời gian kéo dài trung bình|Средняя длительность
Mean intensity|平均強度|平均强度|平均強度|평균 강도|Karaniwang tindi|Intensitas rata-rata|Keamatan purata|Cường độ trung bình|Средняя интенсивность
Maximum intensity|最大強度|最大强度|最大強度|최대 강도|Pinakamataas na tindi|Intensitas maksimum|Keamatan maksimum|Cường độ lớn nhất|Максимальная интенсивность
Cumulative intensity|積算強度|累积强度|累積強度|누적 강도|Naipong tindi|Intensitas kumulatif|Keamatan terkumpul|Cường độ tích lũy|Суммарная интенсивность
Map variable|表示変数|地图变量|地圖變數|지도 변수|Variable sa mapa|Variabel peta|Pemboleh ubah peta|Biến trên bản đồ|Показатель на карте
Temperature record|水温データ|温度记录|溫度記錄|수온 자료|Tala ng temperatura|Rekaman suhu|Rekod suhu|Dữ liệu nhiệt độ|Данные температуры
Ecoregion|生態地域|生态区|生態區|생태지역|Ekolohikal na rehiyon|Ekoregion|Ekowilayah|Vùng sinh thái|Экорегион
All ecoregions|全生態地域|全部生态区|全部生態區|모든 생태지역|Lahat ng rehiyon|Semua ekoregion|Semua ekowilayah|Tất cả vùng sinh thái|Все экорегионы
Habitat|生息地|生境|棲地|서식지|Tirahan|Habitat|Habitat|Sinh cảnh|Местообитание
Coral|サンゴ|珊瑚|珊瑚|산호|Bahura|Karang|Karang|San hô|Кораллы
Coral reefs|サンゴ礁|珊瑚礁|珊瑚礁|산호초|Mga bahura|Terumbu karang|Terumbu karang|Rạn san hô|Коралловые рифы
Seagrass|海草|海草|海草|잘피|Damong-dagat|Lamun|Rumput laut|Cỏ biển|Морские травы
Mangrove|マングローブ|红树林|紅樹林|맹그로브|Bakawan|Mangrove|Bakau|Rừng ngập mặn|Мангры
Mangroves|マングローブ|红树林|紅樹林|맹그로브|Mga bakawan|Mangrove|Bakau|Rừng ngập mặn|Мангры
Kelp & seaweeds|コンブ・大型海藻|海带与大型海藻|海帶與大型海藻|켈프 및 해조류|Kelp at mga lumot-dagat|Kelp dan makroalga|Kelp dan rumpai laut|Tảo bẹ và rong biển|Ламинарии и макроводоросли
Basemap|背景地図|底图|底圖|배경 지도|Batayang mapa|Peta dasar|Peta asas|Bản đồ nền|Подложка карты
Satellite imagery|衛星画像|卫星影像|衛星影像|위성 영상|Larawan ng satelayt|Citra satelit|Imej satelit|Ảnh vệ tinh|Спутниковые снимки
Coastline|海岸線|海岸线|海岸線|해안선|Baybayin|Garis pantai|Garis pantai|Đường bờ biển|Береговая линия
Habitat coverage|生息地分布|生境覆盖|棲地覆蓋|서식지 분포|Saklaw ng tirahan|Cakupan habitat|Liputan habitat|Phân bố sinh cảnh|Распределение местообитаний
More filters|詳細条件|更多筛选|更多篩選|추가 필터|Iba pang salaan|Filter lain|Penapis lain|Bộ lọc khác|Другие фильтры
From|開始|从|從|시작|Mula|Dari|Dari|Từ|С
To|終了|至|至|종료|Hanggang|Sampai|Hingga|Đến|По
Annual|年別|年度|年度|연간|Taunan|Tahunan|Tahunan|Hàng năm|По годам
Monthly|月別|月度|月度|월간|Buwanan|Bulanan|Bulanan|Hàng tháng|По месяцам
Daily|日別|每日|每日|일별|Araw-araw|Harian|Harian|Hàng ngày|Ежедневно
days|日|天|天|일|araw|hari|hari|ngày|дней
days / year|日／年|天／年|天／年|일/년|araw / taon|hari / tahun|hari / tahun|ngày / năm|дней / год
First five years|最初の5年|最初五年|最初五年|첫 5년|Unang limang taon|Lima tahun pertama|Lima tahun pertama|Năm năm đầu|Первые пять лет
Last five years|直近5年|最近五年|最近五年|최근 5년|Huling limang taon|Lima tahun terakhir|Lima tahun terakhir|Năm năm cuối|Последние пять лет
Change between these periods|両期間の差|两个时期之差|兩個時期之差|두 기간의 차이|Pagbabago sa dalawang panahon|Perubahan antarkurun|Perubahan antara tempoh|Chênh lệch giữa hai giai đoạn|Разница между периодами
Highest year|最大の年|最高年份|最高年份|최고 연도|Pinakamataas na taon|Tahun tertinggi|Tahun tertinggi|Năm cao nhất|Год максимума
Observed and fitted variation|観測値とモデル適合値|观测与模型拟合变化|觀測與模型擬合變化|관측값과 모형 적합값|Naobserbahan at naangkop na pagbabago|Perubahan teramati dan hasil model|Perubahan diperhatikan dan padanan model|Biến động quan trắc và mô hình|Наблюдения и модель
Climate associations and long-term change|気候との関連と長期変化|气候关联与长期变化|氣候關聯與長期變化|기후 연관성과 장기 변화|Ugnayan sa klima at pangmatagalang pagbabago|Hubungan iklim dan perubahan jangka panjang|Hubungan iklim dan perubahan jangka panjang|Liên hệ khí hậu và thay đổi dài hạn|Связь с климатом и долгосрочные изменения
Share of variation|変動の内訳|变化占比|變化占比|변동 비중|Bahagi ng pagbabago|Porsi variasi|Bahagian variasi|Tỷ lệ biến động|Доля вариации
Upcoming-season probabilities|次季節の確率|下一季概率|下一季機率|다음 계절 확률|Mga posibilidad sa susunod na panahon|Peluang musim berikutnya|Kebarangkalian musim berikutnya|Xác suất mùa tới|Вероятности на следующий сезон
Seasonal probability|季節確率|季节概率|季節機率|계절 확률|Posibilidad sa panahon|Peluang musiman|Kebarangkalian musim|Xác suất theo mùa|Сезонная вероятность
Historical baseline|過去の基準確率|历史基准|歷史基準|과거 기준|Makasaysayang batayan|Acuan historis|Garis asas sejarah|Mức nền lịch sử|Исторический уровень
Selected pixel|選択セル|所选网格|所選網格|선택한 격자|Napiling selula|Sel terpilih|Sel dipilih|Ô đã chọn|Выбранная ячейка
Overall by habitat|生息地別・海域全体|各生境总体|各棲地整體|서식지별 전체|Kabuuan ayon sa tirahan|Keseluruhan per habitat|Keseluruhan mengikut habitat|Tổng thể theo sinh cảnh|В целом по местообитаниям
Ecoregion by habitat|生態地域・生息地別|各生态区和生境|各生態區與棲地|생태지역 및 서식지별|Rehiyon ayon sa tirahan|Ekoregion per habitat|Ekowilayah mengikut habitat|Vùng sinh thái theo sinh cảnh|По экорегионам и местообитаниям
Blue: past tests · dotted: next season · grey: historical chance|青：過去の検証 · 点線：次季節 · 灰：基準確率|蓝：历史检验 · 点线：下一季 · 灰：历史概率|藍：歷史檢驗 · 點線：下一季 · 灰：歷史機率|파랑: 과거 검증 · 점선: 다음 계절 · 회색: 과거 확률|Asul: dating pagsusuri · tuldok: susunod na panahon · abo: dating posibilidad|Biru: uji masa lalu · titik: musim berikutnya · abu-abu: peluang historis|Biru: ujian lalu · titik: musim berikutnya · kelabu: peluang sejarah|Xanh: kiểm định cũ · chấm: mùa tới · xám: xác suất lịch sử|Синий: прошлые проверки · пунктир: следующий сезон · серый: историческая вероятность
Create point report (PDF)|地点レポートを作成（PDF・英語）|生成点位报告（PDF，英语）|產生點位報告（PDF，英語）|지점 보고서 생성(PDF, 영어)|Gumawa ng ulat (PDF, Ingles)|Buat laporan titik (PDF, Inggris)|Bina laporan titik (PDF, Inggeris)|Tạo báo cáo điểm (PDF, tiếng Anh)|Создать отчёт по точке (PDF, английский)
Download original|原画像をダウンロード|下载原图|下載原圖|원본 다운로드|I-download ang orihinal|Unduh asli|Muat turun asal|Tải ảnh gốc|Скачать оригинал
Download CSV|CSVをダウンロード|下载 CSV|下載 CSV|CSV 다운로드|I-download ang CSV|Unduh CSV|Muat turun CSV|Tải CSV|Скачать CSV
Contact|連絡先|联系|聯絡|연락처|Makipag-ugnayan|Kontak|Hubungi|Liên hệ|Контакты
Night view|夜間表示|夜间模式|夜間模式|야간 모드|Madilim na tanaw|Mode malam|Paparan malam|Chế độ tối|Тёмная тема
Day view|昼間表示|日间模式|日間模式|주간 모드|Maliwanag na tanaw|Mode siang|Paparan siang|Chế độ sáng|Светлая тема
Pause motion|動きを停止|暂停动画|暫停動畫|움직임 정지|Ihinto ang galaw|Jeda gerakan|Jeda gerakan|Dừng chuyển động|Остановить анимацию
Enable motion|動きを有効化|启用动画|啟用動畫|움직임 켜기|Paganahin ang galaw|Aktifkan gerakan|Aktifkan gerakan|Bật chuyển động|Включить анимацию`;
  const codes=['ja','zh-Hans','zh-Hant','ko','fil','id','ms','vi','ru'],dictionaries=Object.fromEntries(Object.keys(names).map(k=>[k,{}]));
  for(const line of rows.split('\n')){const [key,...values]=line.split('|');codes.forEach((code,i)=>dictionaries[code][key]=values[i]);}
  const extra=`Data|データ|数据|資料|자료|Datos|Data|Data|Dữ liệu|Данные
Scale|表示尺度|尺度|尺度|척도|Sukat|Skala|Skala|Thang đo|Масштаб
Time step|時間間隔|时间步长|時間間隔|시간 간격|Pagitan ng oras|Langkah waktu|Sela masa|Bước thời gian|Шаг времени
Standardised|標準化|标准化|標準化|표준화|Pamantayang halaga|Terstandar|Terpiawai|Chuẩn hóa|Стандартизовано
Original values|元の値|原始值|原始值|원래 값|Orihinal na halaga|Nilai asli|Nilai asal|Giá trị gốc|Исходные значения
Current year|今年|今年|今年|올해|Kasalukuyang taon|Tahun berjalan|Tahun semasa|Năm hiện tại|Текущий год
Full record|全期間|完整记录|完整記錄|전체 기록|Buong tala|Seluruh rekaman|Seluruh rekod|Toàn bộ dữ liệu|Весь ряд
Study archive|研究用アーカイブ|研究档案|研究檔案|연구 자료실|Arkibo ng pag-aaral|Arsip kajian|Arkib kajian|Kho dữ liệu nghiên cứu|Архив исследования
Latest monthly feeds|最新の月次データ|最新月度数据|最新月度資料|최신 월간 자료|Pinakabagong buwanang datos|Data bulanan terbaru|Data bulanan terkini|Dữ liệu tháng mới nhất|Последние месячные данные
Related published research|関連する発表論文|相关已发表研究|相關已發表研究|관련 출판 연구|Kaugnay na nalathalang pag-aaral|Penelitian terbit terkait|Kajian terbitan berkaitan|Nghiên cứu đã công bố liên quan|Связанные публикации
News from the sources|発信元からのニュース|来源新闻|來源新聞|출처 기관의 소식|Balita mula sa mga sanggunian|Berita dari sumber|Berita daripada sumber|Tin từ các nguồn|Новости из первоисточников
Topic|主題|主题|主題|주제|Paksa|Topik|Topik|Chủ đề|Тема
All topics|全主題|全部主题|全部主題|모든 주제|Lahat ng paksa|Semua topik|Semua topik|Tất cả chủ đề|Все темы
Regional studies|地域研究|区域研究|區域研究|지역 연구|Mga pag-aaral sa rehiyon|Kajian regional|Kajian serantau|Nghiên cứu khu vực|Региональные исследования
Habitat impacts|生息地への影響|生境影响|棲地影響|서식지 영향|Epekto sa tirahan|Dampak habitat|Kesan habitat|Tác động đến sinh cảnh|Воздействие на местообитания
Methods and drivers|方法と要因|方法与驱动因素|方法與驅動因素|방법과 요인|Pamamaraan at mga salik|Metode dan pendorong|Kaedah dan pendorong|Phương pháp và yếu tố chi phối|Методы и факторы
Forecasting|予測|预测|預測|예측|Pagtataya|Prakiraan|Ramalan|Dự báo|Прогнозирование
Play slideshow|スライドショーを再生|播放幻灯片|播放幻燈片|슬라이드 쇼 재생|I-play ang mga larawan|Putar tayangan foto|Mainkan tayangan foto|Phát trình chiếu|Запустить показ
Pause slideshow|スライドショーを停止|暂停幻灯片|暫停幻燈片|슬라이드 쇼 정지|Ihinto ang mga larawan|Jeda tayangan foto|Jeda tayangan foto|Dừng trình chiếu|Остановить показ
Actual pixels|元の画素で表示|实际像素|實際像素|실제 픽셀|Aktuwal na mga pixel|Piksel asli|Piksel sebenar|Điểm ảnh gốc|Исходные пиксели
Fit to screen|画面に合わせる|适应屏幕|符合螢幕|화면에 맞추기|Iangkop sa screen|Sesuaikan layar|Muat pada skrin|Vừa màn hình|По размеру экрана
Closest photo in the collection|収録写真で最も近い場所|图库中距离最近的照片|圖庫中距離最近的照片|사진 모음 중 가장 가까운 사진|Pinakamalapit na larawan sa koleksiyon|Foto terdekat dalam koleksi|Foto terdekat dalam koleksi|Ảnh gần nhất trong bộ sưu tập|Ближайшее фото в коллекции
Distance to the photo coordinate. The image is separate from this heatwave cell.|写真の座標までの距離です。選択セルそのものの写真ではありません。|距离按照片坐标计算。照片与所选热浪网格分开。|距離按照片座標計算。照片與所選熱浪網格分開。|사진 좌표까지의 거리입니다. 선택한 열파 격자의 사진과는 다릅니다.|Layo sa koordinado ng larawan. Hiwalay ang larawan sa selula ng init.|Jarak ke koordinat foto. Foto terpisah dari sel gelombang panas ini.|Jarak ke koordinat foto. Foto berasingan daripada sel gelombang haba ini.|Khoảng cách tới tọa độ ảnh. Ảnh tách biệt với ô nắng nóng biển này.|Расстояние до координат фотографии. Фото не относится к самой выбранной ячейке.
Distance to the named photo area; its position is approximate.|写真の地名で示す範囲までのおよその距離です。|到照片所注明区域的距离，位置为近似值。|到照片所註明區域的距離，位置為近似值。|사진에 명시된 지역까지의 거리이며 위치는 대략적입니다.|Layo sa lugar na nakapangalan sa larawan; tinatayang lokasyon lamang.|Jarak ke area foto yang disebutkan; posisi perkiraan.|Jarak ke kawasan foto yang dinamakan; kedudukan anggaran.|Khoảng cách tới vùng ghi trong nguồn ảnh; vị trí gần đúng.|Расстояние до указанного района съёмки; положение приблизительное.
Reefs, seagrass, mangroves and kelp|サンゴ礁・海草・マングローブ・コンブ|珊瑚礁、海草、红树林与海带|珊瑚礁、海草、紅樹林與海帶|산호초, 잘피, 맹그로브, 켈프|Bahura, damong-dagat, bakawan at kelp|Terumbu, lamun, mangrove dan kelp|Terumbu, rumput laut, bakau dan kelp|Rạn san hô, cỏ biển, rừng ngập mặn và tảo bẹ|Рифы, морские травы, мангры и ламинарии
Daily OISST SST|OISSTの日別水温|OISST 每日海温|OISST 每日海溫|OISST 일별 해수면온도|Arawang temperatura ng OISST|SST harian OISST|SST harian OISST|Nhiệt độ mặt biển OISST hàng ngày|Суточная ТПО OISST
Monthly mean SST|月平均水温|月平均海温|月平均海溫|월평균 해수면온도|Buwanang karaniwang temperatura|Rata-rata SST bulanan|Purata SST bulanan|Nhiệt độ mặt biển trung bình tháng|Среднемесячная ТПО
Monthly MHW days|月別海洋熱波日数|月度热浪天数|月度熱浪天數|월별 해양열파 일수|Buwanang mga araw ng init|Hari gelombang panas bulanan|Hari gelombang haba bulanan|Số ngày nắng nóng biển hàng tháng|Месячные дни волн тепла
Find a coastal place|沿岸の場所を検索|查找沿海地点|尋找沿海地點|연안 장소 찾기|Maghanap ng lugar sa baybayin|Cari tempat pesisir|Cari tempat pesisir|Tìm địa điểm ven biển|Найти место на побережье
Show 20 hotspots|上位20地点を表示|显示前20个高值点|顯示前20個高值點|상위 20개 지점 보기|Ipakita ang 20 matataas na lugar|Tampilkan 20 titik tertinggi|Papar 20 titik tertinggi|Hiển thị 20 điểm giá trị cao|Показать 20 максимумов
Draw selection|範囲を描く|绘制选择范围|繪製選取範圍|선택 영역 그리기|Iguhit ang pagpili|Gambar pilihan|Lukis pilihan|Vẽ vùng chọn|Нарисовать область
Use map extent|表示範囲を選択|使用地图范围|使用地圖範圍|지도 범위 사용|Gamitin ang lawak ng mapa|Gunakan cakupan peta|Gunakan liputan peta|Dùng phạm vi bản đồ|Выбрать видимую область
No comparison|比較なし|不比较|不比較|비교 없음|Walang paghahambing|Tanpa perbandingan|Tiada perbandingan|Không so sánh|Без сравнения
Compare left year|左側の比較年|左侧比较年份|左側比較年份|왼쪽 비교 연도|Taon sa kaliwang paghahambing|Tahun pembanding kiri|Tahun bandingan kiri|Năm so sánh bên trái|Год сравнения слева
Read at source|発信元を読む|阅读原文|閱讀原文|원문 보기|Basahin sa sanggunian|Baca di sumber|Baca di sumber|Đọc tại nguồn|Читать в источнике
Satellite maps, habitat-pixel histories and seasonal climate probabilities.|衛星地図、生息地セルの履歴、季節ごとの確率。|卫星地图、生境网格历史和季节概率。|衛星地圖、棲地網格歷史與季節機率。|위성 지도, 서식지 격자 기록, 계절별 확률.|Mapa ng satelayt, tala ng mga selula at posibilidad ayon sa panahon.|Peta satelit, riwayat sel habitat dan peluang musiman.|Peta satelit, sejarah sel habitat dan kebarangkalian musim.|Bản đồ vệ tinh, lịch sử ô sinh cảnh và xác suất theo mùa.|Спутниковые карты, ряды по ячейкам и сезонные вероятности.`;
  for(const line of extra.split('\n')){const [key,...values]=line.split('|');codes.forEach((code,i)=>dictionaries[code][key]=values[i]);}
  dictionaries.fa={'Map':'نقشه','Seasonal outlook':'چشم‌انداز فصلی','Climate indices':'شاخص‌های اقلیمی','Habitat photographs':'عکس‌های زیستگاه','Research & news':'پژوهش و خبر','Data & methods':'داده‌ها و روش‌ها','Coastal Habitat Heatwave Atlas':'اطلس موج گرمای دریایی زیستگاه‌های ساحلی','Choose an area on the map':'یک ناحیه روی نقشه انتخاب کنید','Draw a rectangle':'یک مستطیل رسم کنید','Use map view':'استفاده از نمای نقشه','Explore all areas':'نمایش همه نواحی','Study area':'منطقه مطالعه','Heatwave days':'روزهای موج گرما','Coral':'مرجان','Seagrass':'علف دریایی','Mangrove':'حرا','Habitat':'زیستگاه','More filters':'فیلترهای بیشتر','Heatwaves through time':'موج‌های گرما در گذر زمان','Night view':'نمای شب','Day view':'نمای روز'};
  for(const d of Object.values(dictionaries)){d.coral=d.Coral;d.seagrass=d.Seagrass;d.mangrove=d.Mangrove;d.kelp_macroalgae=d['Kelp & seaweeds'];}
  window.AtlasLocales={names,dictionaries};
})();
