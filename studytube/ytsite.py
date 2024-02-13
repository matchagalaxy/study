from flask import Flask, jsonify, render_template, request
import pyodbc 
from datetime import datetime
app = Flask(__name__)

# Database connection details
server = 'DESKTOP-B30EECT'  # e.g., 'localhost' or 'your_server\instance_name'
database = 'youtube' 

# Connect to your database using Windows Authentication
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                      f'SERVER={server};'
                      f'DATABASE={database};'
                      'Trusted_Connection=yes;')




# ALL VIDEOS PAGE

@app.route('/')
def index():
    return render_template('homepage.html')

@app.route('/videos')
def show_videos():
    return render_template('videos.html')


@app.route('/videos/<int:page>', methods=['GET'])
def get_videos(page):
    per_page = 20
    offset = (page - 1) * per_page
    end = offset + per_page

    try:
        # Create a new cursor for the first query
        with conn.cursor() as cursor:
            cursor.execute("WITH OrderedVideos AS (SELECT *, ROW_NUMBER() OVER (ORDER BY upload_date) AS RowNum FROM Videos) SELECT * FROM OrderedVideos WHERE RowNum BETWEEN ? AND ?", (offset + 1, end))
            videos = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        
        # Create another new cursor for the second query
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Videos")
            total_videos = cursor.fetchone()[0]
            total_pages = (total_videos + per_page - 1) // per_page

        return jsonify({"videos": videos, "total_pages": total_pages})

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Filter And Sort

@app.route('/api/videos', methods=['GET'])
def filter_and_sort_videos():
    filter_tag = request.args.get('filter_tag', 'ALL')
    sort_by = request.args.get('sort_by', 'upload_date')
    allowed_sort_columns = ['upload_date', 'view_count', 'likes', 'video_length']
    per_page = 20
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * per_page

    if sort_by not in allowed_sort_columns:
        return jsonify({"error": "Invalid sort parameter"}), 400

    try:
        with conn.cursor() as cursor:
            sql_query = "SELECT DISTINCT v.* FROM Videos v "
            if filter_tag != 'ALL':
                sql_query += "JOIN Tips t ON v.doc = t.doc WHERE t.category = ? "
            sql_query += "ORDER BY v.{} DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY".format(sort_by)
            params = (filter_tag, offset, per_page) if filter_tag != 'ALL' else (offset, per_page)

            cursor.execute(sql_query, params)
            videos = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

            # Build and execute the count query
            count_query = "SELECT COUNT(DISTINCT v.doc) FROM Videos v "
        if filter_tag != 'ALL':
            count_query += "JOIN Tips t ON v.doc = t.doc WHERE t.category = ?"
            cursor.execute(count_query, (filter_tag,))
        else:
            cursor.execute(count_query)

        total_videos = cursor.fetchone()[0]
        total_pages = (total_videos + per_page - 1) // per_page

        return jsonify({"videos": videos, "total_pages": total_pages})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# TAGS

@app.route('/api/tags', methods=['GET'])
def get_tags():
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT category FROM Tips")
            categories = [row[0] for row in cursor.fetchall()]
        return jsonify(categories)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    





# VIDEO DETAIL PAGE
from urllib.parse import urlparse, parse_qs

@app.route('/video/<int:doc>', methods=['GET'])
def video_detail(doc):
    try:
        with conn.cursor() as cursor:
            # Fetch video details
            cursor.execute("SELECT * FROM Videos WHERE doc = ?", (doc,))
            video = dict(zip([column[0] for column in cursor.description], cursor.fetchone()))
            if video.get('view_count') is not None:
                video['view_count'] = "{:,}".format(video['view_count'])
            if isinstance(video['upload_date'], datetime):
                    video['upload_date'] = video['upload_date'].strftime('%Y-%m-%d')
            # Extract the video ID from the URL
            video_url = video.get('url')
            parsed_url = urlparse(video_url)
            video_id = parse_qs(parsed_url.query)['v'][0]

            # Fetch tips related to this video
            cursor.execute("SELECT tip FROM Tips WHERE doc = ?", (doc,))
            tips = [row[0] for row in cursor.fetchall()] 

            # Fetch transcript
            cursor.execute("SELECT transcript FROM Transcripts WHERE doc = ?", (doc,))
            transcript = cursor.fetchone()[0] if cursor.rowcount != 0 else "No transcript available"

            # Fetch tags (distinct categories) related to this video
            cursor.execute("SELECT DISTINCT category FROM Tips WHERE doc = ?", (doc,))
            tags = [row[0] for row in cursor.fetchall()]

        return render_template('video_detail.html', video=video, tips=tips, transcript=transcript, tags=tags, video_id=video_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# SEARCH
    
@app.route('/api/search', methods=['GET'])
def search_videos():
    search_query = request.args.get('query', '').lower()
    per_page = 20
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * per_page

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT v.*, 
                    SUM(CASE 
                        WHEN LOWER(v.title) LIKE ? THEN 8
                        WHEN LOWER(v.channel_name) LIKE ? THEN 5
                        WHEN LOWER(t.category) LIKE ? THEN 4
                        WHEN LOWER(t.tip) LIKE ? THEN 3
                        ELSE 0
                    END) AS relevance
                FROM Videos v
                LEFT JOIN Tips t ON v.doc = t.doc
                GROUP BY v.doc, v.title, v.upload_date, v.view_count, v.likes, v.comments, v.channel_name, v.url, v.video_length, v.raw_title, v.channel_id
                HAVING SUM(CASE 
                        WHEN LOWER(v.title) LIKE ? THEN 8
                        WHEN LOWER(v.channel_name) LIKE ? THEN 5
                        WHEN LOWER(t.category) LIKE ? THEN 4
                        WHEN LOWER(t.tip) LIKE ? THEN 3
                        ELSE 0
                    END) > 0
                ORDER BY relevance DESC, v.upload_date DESC
                OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                """, ['%' + search_query + '%'] * 8 + [offset, per_page])
            videos = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

            # Additional query to count total search results
            cursor.execute("""
                SELECT COUNT(DISTINCT v.doc)
                            FROM Videos v
                            LEFT JOIN Tips t ON v.doc = t.doc
                            WHERE LOWER(v.title) LIKE ?
                            OR LOWER(v.channel_name) LIKE ?
                            OR LOWER(t.category) LIKE ?
                            OR LOWER(t.tip) LIKE ?

            """, ['%' + search_query + '%'] * 4)
            total_results = cursor.fetchone()[0]

            return jsonify({"videos": videos, "total_results": total_results})

    except Exception as e:
        app.logger.error('Error in search_videos: %s', str(e))
        return jsonify({"error": str(e)}), 500







if __name__ == '__main__':
    app.run(debug=True)
