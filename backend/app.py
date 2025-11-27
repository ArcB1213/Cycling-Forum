import os
from flask import Flask, jsonify
from flask_cors import CORS

# 从新文件中导入 db 和 migrate 实例
from models.extensions import db, migrate

# 导入你的模型
from models.models import Race, Edition, Stage, StageResult, Rider, Team

def create_app():
    """
    应用工厂函数
    """
    app = Flask(__name__)
    
    # --- 1. 配置 ---
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'cycling_stats.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # --- 2. 初始化扩展 ---
    # 将 app 实例与 db 和 migrate 关联
    db.init_app(app)
    migrate.init_app(app, db)
    
    # --- 3. 启用 CORS ---
    # 允许所有来源的跨域请求，方便前后端分离开发
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # --- 4. 定义 API 路由 ---
    
    @app.route('/')
    def index():
        return "欢迎来到三大环赛数据 API！"

    @app.route('/api/races', methods=['GET'])
    def get_races():
        """
        获取所有赛事 (例如: 环法, 环意)
        """
        races = Race.query.order_by(Race.race_id).all()
        return jsonify([race.to_dict() for race in races])

    @app.route('/api/races/<int:race_id>/editions', methods=['GET'])
    def get_editions(race_id):
        """
        获取某一赛事的所有届数 (年份)
        """
        race = Race.query.get_or_404(race_id)
        editions = Edition.query.filter_by(race_id=race.race_id).order_by(Edition.year.desc()).all()
        return jsonify({
            'race': race.race_name,
            'editions': [e.to_dict() for e in editions]
        })

    @app.route('/api/editions/<int:edition_id>/stages', methods=['GET'])
    def get_stages(edition_id):
        """
        获取某一届赛事的所有赛段
        """
        edition = Edition.query.get_or_404(edition_id)
        stages = Stage.query.filter_by(edition_id=edition.edition_id).order_by(Stage.stage_number).all()
        
        # 使用 to_dict() 进行序列化
        return jsonify({
            'edition_year': edition.year,
            'race_name': edition.race.race_name,
            'stages': [s.to_dict() for s in stages]
        })

    @app.route('/api/stages/<int:stage_id>/results', methods=['GET'])
    def get_stage_results(stage_id):
        """
        获取某一赛段的完整成绩单 (按排名)
        """
        stage = Stage.query.get_or_404(stage_id)
        
        # 这个查询会用到你之前创建的 (stage_id, rank) 复合索引！
        results = StageResult.query.filter_by(stage_id=stage.stage_id).order_by(StageResult.rank).all()
        
        # 使用 to_dict(include_relations=True) 来获取车手和车队名称
        return jsonify({
            'stage_info': stage.to_dict(),
            'results': [res.to_dict(include_relations=True) for res in results]
        })

    @app.route('/api/riders', methods=['GET'])
    def get_riders():
        """
        获取所有车手列表
        """
        riders = Rider.query.order_by(Rider.rider_name).all()
        return jsonify([rider.to_dict() for rider in riders])

    @app.route('/api/riders/<int:rider_id>', methods=['GET'])
    def get_rider_detail(rider_id):
        """
        获取单个车手的详细统计信息
        """
        rider = Rider.query.get_or_404(rider_id)
        
        # 统计参赛场次（不同赛段数量）
        total_races = db.session.query(StageResult.stage_id).filter_by(rider_id=rider.rider_id).distinct().count()
        
        # 统计赛段冠军数（rank=1）
        stage_wins = StageResult.query.filter_by(rider_id=rider.rider_id, rank=1).count()
        
        # 获取效力过的所有车队（去重）
        team_ids = db.session.query(StageResult.team_id).filter_by(rider_id=rider.rider_id).distinct().all()
        teams = [Team.query.get(tid[0]).to_dict() for tid in team_ids if Team.query.get(tid[0])]
        
        return jsonify({
            'rider': rider.to_dict(),
            'stats': {
                'total_races': total_races,
                'stage_wins': stage_wins,
                'teams': teams
            }
        })

    @app.route('/api/riders/<int:rider_id>/races', methods=['GET'])
    def get_rider_races(rider_id):
        """
        获取车手的所有参赛记录
        """
        rider = Rider.query.get_or_404(rider_id)
        
        # 获取该车手所有参赛记录，按年份和赛段排序
        results = (StageResult.query
                   .filter_by(rider_id=rider.rider_id)
                   .join(Stage, StageResult.stage_id == Stage.stage_id)
                   .join(Edition, Stage.edition_id == Edition.edition_id)
                   .join(Race, Edition.race_id == Race.race_id)
                   .order_by(Edition.year.desc(), Stage.stage_number)
                   .all())
        
        race_records = []
        for result in results:
            stage = result.stage
            edition = stage.edition
            race = edition.race
            team = result.team
            
            race_records.append({
                'result_id': result.result_id,
                'race_name': race.race_name,
                'year': edition.year,
                'stage_number': stage.stage_number,
                'stage_route': stage.stage_route,
                'rank': result.rank,
                'time_in_seconds': result.time_in_seconds,
                'team_name': team.team_name if team else 'Unknown'
            })
        
        return jsonify({
            'rider': rider.to_dict(),
            'race_records': race_records
        })

    @app.route('/api/riders/<int:rider_id>/wins', methods=['GET'])
    def get_rider_wins(rider_id):
        """
        获取车手的所有赛段冠军记录
        """
        rider = Rider.query.get_or_404(rider_id)
        
        # 获取所有rank=1的记录
        wins = (StageResult.query
                .filter_by(rider_id=rider.rider_id, rank=1)
                .join(Stage, StageResult.stage_id == Stage.stage_id)
                .join(Edition, Stage.edition_id == Edition.edition_id)
                .join(Race, Edition.race_id == Race.race_id)
                .order_by(Edition.year.desc(), Stage.stage_number)
                .all())
        
        win_records = []
        for win in wins:
            stage = win.stage
            edition = stage.edition
            race = edition.race
            team = win.team
            
            win_records.append({
                'result_id': win.result_id,
                'race_name': race.race_name,
                'year': edition.year,
                'stage_number': stage.stage_number,
                'stage_route': stage.stage_route,
                'time_in_seconds': win.time_in_seconds,
                'team_name': team.team_name if team else 'Unknown'
            })
        
        return jsonify({
            'rider': rider.to_dict(),
            'win_records': win_records
        })

    return app

# --- 5. 运行 ---
# 通过 'flask run' 命令启动时，会查找这个 app 实例
app = create_app()

if __name__ == '__main__':
    # 允许通过 'python app.py' 直接运行
    app.run(debug=True)